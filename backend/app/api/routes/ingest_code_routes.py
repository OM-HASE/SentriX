from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.graph.graph_builder import build_repository_graph
from app.graph.graph_memory import repository_graph_memory
from app.rag.embeddings import embedding_model
from app.rag.vector_store import collection
from app.core.cache import embedding_cache
from app.services.universal_chunker import universal_chunk_code
from app.services.persistence_service import save_graph_memory

logger = logging.getLogger(__name__)

router = APIRouter()

# =========================================
# SUPPORTED LANGUAGES
# =========================================

EXTENSION_TO_LANGUAGE = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "javascript",
    ".jsx":  "javascript",
    ".tsx":  "javascript",
    ".java": "java",
    ".go":   "go",
    ".rs":   "rust",
    ".cs":   "csharp",
    ".c":    "c",
    ".cpp":  "cpp",
    ".h":    "c",
}


# =========================================
# SCHEMAS
# =========================================

class CodeFile(BaseModel):
    """
    One source file submitted as JSON.

    filename : e.g. "auth.py", "UserService.java"
    content  : full source code as a string
    language : optional — inferred from filename extension if omitted
    """
    filename : str
    content  : str
    language : str | None = None


class IngestCodeRequest(BaseModel):
    """
    Submit one or more source files directly as JSON.
    No repository or filesystem access required.

    Example:
    {
        "project_name": "my-service",
        "files": [
            {"filename": "app.py",  "content": "..."},
            {"filename": "auth.py", "content": "..."}
        ]
    }
    """
    project_name : str = "inline-project"
    files        : list[CodeFile]


class IngestCodeResponse(BaseModel):
    message          : str
    project_name     : str
    total_files      : int
    total_chunks     : int
    languages_found  : list[str]
    graph_node_count : int
    graph_edge_count : int


# =========================================
# ROUTE
# =========================================

@router.post("/ingest-code", response_model=IngestCodeResponse)
def ingest_code(data: IngestCodeRequest) -> IngestCodeResponse:
    """
    Ingest source files submitted directly in the request body.

    Use this when you:
      - don't have a local repo path
      - want to test with hand-crafted code snippets
      - are developing/debugging the RCA pipeline

    After calling this, use POST /api/rca with just an error_log
    to run full cognitive root cause analysis.
    """

    if not data.files:
        raise HTTPException(
            status_code=422,
            detail="At least one file is required in 'files'."
        )

    # ---- normalize files ----
    normalized = _normalize_files(data.files)

    if not normalized:
        raise HTTPException(
            status_code=422,
            detail=(
                "No files had recognizable language. "
                "Supported extensions: "
                + str(sorted(EXTENSION_TO_LANGUAGE.keys()))
            )
        )

    logger.info(
        "Ingesting %d inline files for project '%s'.",
        len(normalized), data.project_name
    )

    # ---- build unified graph ----
    unified_graph = _build_graph(normalized, data.project_name)

    # ---- embed + store in ChromaDB ----
    total_chunks = _embed_and_store(normalized, data.project_name)

    # ---- persist ----
    repository_graph_memory["active_graph"]     = unified_graph
    repository_graph_memory["repo_name"]        = data.project_name
    repository_graph_memory["repo_path"]        = "(inline)"
    repository_graph_memory["repository_index"] = [
        {
            "file_name":   f["filename"],
            "rel_path":    f["filename"],
            "file_path":   f["filename"],
            "language":    f["language"],
            "source_code": f["content"],
        }
        for f in normalized
    ]

    save_graph_memory()

    languages    = sorted({f["language"] for f in normalized})
    node_count   = len(unified_graph.get("nodes", {}))
    edge_count   = len(unified_graph.get("edges", []))

    logger.info(
        "Inline ingest done: %d files, %d chunks, "
        "%d nodes, %d edges.",
        len(normalized), total_chunks, node_count, edge_count
    )

    return IngestCodeResponse(
        message          = "Code ingested successfully. Ready for /api/rca.",
        project_name     = data.project_name,
        total_files      = len(normalized),
        total_chunks     = total_chunks,
        languages_found  = languages,
        graph_node_count = node_count,
        graph_edge_count = edge_count,
    )


# =========================================
# HELPERS
# =========================================

def _normalize_files(files: list[CodeFile]) -> list[dict]:
    """
    Resolves language from filename extension when not explicitly set.
    Drops files with unsupported extensions.
    """
    result = []

    for f in files:
        if not f.content or not f.content.strip():
            continue

        language = f.language

        if not language:
            ext = Path(f.filename).suffix.lower()
            language = EXTENSION_TO_LANGUAGE.get(ext)

        if not language:
            logger.debug(
                "Skipping '%s' — unrecognized extension.", f.filename
            )
            continue

        result.append({
            "filename": f.filename,
            "content":  f.content,
            "language": language,
        })

    return result


def _build_graph(files: list[dict], project_name: str) -> dict:
    """
    Builds a unified graph from all submitted files.
    Same merge strategy as ingest_routes._build_unified_graph.
    """
    merged_nodes : dict = {}
    merged_edges : list = []
    edge_set     : set  = set()

    for file_info in files:
        try:
            file_graph = build_repository_graph(file_info["content"])
        except Exception as exc:
            logger.warning(
                "Graph build failed for '%s': %s — skipping.",
                file_info["filename"], exc
            )
            continue

        for node_id, node_data in file_graph.get("nodes", {}).items():
            if node_id not in merged_nodes:
                merged_nodes[node_id] = node_data
                meta = merged_nodes[node_id].setdefault("metadata", {})
                if not meta.get("file_path"):
                    meta["file_path"] = file_info["filename"]
                    meta["file_name"] = file_info["filename"]
            else:
                meta = merged_nodes[node_id].setdefault("metadata", {})
                defined_in = meta.setdefault("defined_in", [])
                if file_info["filename"] not in defined_in:
                    defined_in.append(file_info["filename"])

        for edge in file_graph.get("edges", []):
            key = (
                edge.get("source", ""),
                edge.get("target", ""),
                edge.get("relationship", ""),
            )
            if key not in edge_set:
                edge_set.add(key)
                merged_edges.append(edge)

    last_graph = repository_graph_memory.get("active_graph", {})
    unified    = {**last_graph}
    unified["nodes"] = merged_nodes
    unified["edges"] = merged_edges
    return unified


def _embed_and_store(files: list[dict], project_name: str) -> int:
    """
    Chunks, embeds, and upserts all files into ChromaDB.
    """
    total = 0

    for file_info in files:
        try:
            chunks = universal_chunk_code(file_info["content"])
        except Exception:
            chunks = [{
                "chunk_id":   1,
                "language":   file_info["language"],
                "type":       "file",
                "start_line": 1,
                "end_line":   file_info["content"].count("\n") + 1,
                "content":    file_info["content"],
            }]

        for chunk in chunks:
            chunk_text = chunk.get("content", "")
            if not chunk_text.strip():
                continue

            cache_key = f"{project_name}::{file_info['filename']}::{chunk_text}"

            if cache_key in embedding_cache:
                embedding = embedding_cache[cache_key]
            else:
                try:
                    embedding = embedding_model.encode(chunk_text).tolist()
                    embedding_cache[cache_key] = embedding
                except Exception as exc:
                    logger.debug("Embedding failed: %s", exc)
                    continue

            chunk_id = f"{project_name}::{file_info['filename']}::{total}"

            try:
                collection.add(
                    ids       = [chunk_id],
                    embeddings= [embedding],
                    documents = [chunk_text],
                    metadatas = [{
                        "file":       file_info["filename"],
                        "language":   file_info["language"],
                        "type":       str(chunk.get("type", "")),
                        "name":       str(chunk.get("name", "")),
                        "start_line": int(chunk.get("start_line") or 0),
                        "end_line":   int(chunk.get("end_line") or 0),
                    }]
                )
                total += 1
            except Exception as exc:
                logger.debug("ChromaDB upsert error: %s", exc)

    return total