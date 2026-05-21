from __future__ import annotations

import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import git

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
# CONSTANTS
# =========================================

REPO_DIR = "cloned_repos"
os.makedirs(REPO_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = {
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
    ".cc":   "cpp",
    ".h":    "c",
    ".hpp":  "cpp",
}

IGNORE_DIRS = {
    "node_modules", "venv", ".venv", ".git", "__pycache__",
    ".next", "dist", "build", ".idea", ".vscode",
    "target",        # Rust / Maven
    "vendor",        # Go modules
    ".gradle",
    "*.egg-info",
}

# Safety cap: skip files larger than 500 KB to avoid
# feeding enormous generated files into the graph builder.
MAX_FILE_BYTES = 500_000


# =========================================
# REQUEST / RESPONSE SCHEMAS
# =========================================

class IngestRepoRequest(BaseModel):
    """
    Ingest a repository into the knowledge graph + vector store.

    Provide exactly one of:
        repo_path  : local folder path (absolute or relative to CWD)
        github_url : public GitHub URL (will be cloned first)
    """
    repo_path  : str | None = None
    github_url : str | None = None


class IngestRepoResponse(BaseModel):
    message          : str
    repo_name        : str
    total_files      : int
    total_chunks     : int
    languages_found  : list[str]
    graph_node_count : int
    graph_edge_count : int


# =========================================
# ROUTE
# =========================================

@router.post("/ingest-repo", response_model=IngestRepoResponse)
def ingest_repository(data: IngestRepoRequest) -> IngestRepoResponse:
    """
    Full pipeline:
      1. Resolve repo path (clone from GitHub if needed)
      2. Walk all supported source files
      3. Build / merge per-file graphs into one unified graph
      4. Embed chunks and upsert into ChromaDB
      5. Persist repository_index in graph memory for
         RepositoryContextExpansionEngine

    Returns summary stats. Idempotent — re-ingesting the same
    repo refreshes the graph and re-embeds (skips cached embeddings).
    """

    # --------------------------------------------------
    # STEP 1 — RESOLVE REPO PATH
    # --------------------------------------------------
    repo_path = _resolve_repo_path(data)

    repo_name = Path(repo_path).name

    # --------------------------------------------------
    # STEP 2 — WALK FILES
    # --------------------------------------------------
    source_files = _collect_source_files(repo_path)

    if not source_files:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No supported source files found in '{repo_path}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS.keys())}"
            )
        )

    logger.info(
        "Ingesting repo '%s' — %d source files found.",
        repo_name, len(source_files)
    )

    # --------------------------------------------------
    # STEP 3 — BUILD UNIFIED GRAPH
    # --------------------------------------------------
    unified_graph, repository_index = _build_unified_graph(
        source_files, repo_path
    )

    # Persist in global memory so all cognition engines can use it
    repository_graph_memory["active_graph"]     = unified_graph
    repository_graph_memory["repository_index"] = repository_index
    repository_graph_memory["repo_name"]        = repo_name
    repository_graph_memory["repo_path"]        = repo_path

    # --------------------------------------------------
    # STEP 4 — EMBED + STORE IN CHROMADB
    # --------------------------------------------------
    total_chunks = _embed_and_store(source_files)

    # --------------------------------------------------
    # STEP 5 — SUMMARY
    # --------------------------------------------------
    languages = sorted({f["language"] for f in source_files})
    node_count = len(unified_graph.get("nodes", {}))
    edge_count = len(unified_graph.get("edges", []))

    logger.info(
        "Repo '%s' ingested: %d files, %d chunks, "
        "%d graph nodes, %d graph edges.",
        repo_name, len(source_files), total_chunks,
        node_count, edge_count
    )

    # Persist graph so it survives server restarts
    save_graph_memory()

    return IngestRepoResponse(
        message          = "Repository ingested successfully.",
        repo_name        = repo_name,
        total_files      = len(source_files),
        total_chunks     = total_chunks,
        languages_found  = languages,
        graph_node_count = node_count,
        graph_edge_count = edge_count,
    )


# =========================================
# HELPERS
# =========================================

def _resolve_repo_path(data: IngestRepoRequest) -> str:
    """
    Returns the local filesystem path to the repository.
    Clones from GitHub if github_url is provided.
    Raises HTTPException on invalid input.
    """

    if data.repo_path and data.github_url:
        raise HTTPException(
            status_code=422,
            detail="Provide either repo_path OR github_url, not both."
        )

    if data.repo_path:
        path = data.repo_path
        if not os.path.isdir(path):
            raise HTTPException(
                status_code=422,
                detail=f"repo_path '{path}' does not exist or is not a directory."
            )
        return path

    if data.github_url:
        return _clone_github_repo(data.github_url)

    raise HTTPException(
        status_code=422,
        detail="Provide repo_path (local path) or github_url."
    )


def _clone_github_repo(github_url: str) -> str:
    """
    Clones the GitHub repo into REPO_DIR.
    Returns the local path. Skips cloning if already present.
    """
    repo_name  = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = os.path.join(REPO_DIR, repo_name)

    if os.path.isdir(clone_path):
        logger.info(
            "Repo '%s' already cloned at '%s' — using existing copy.",
            repo_name, clone_path
        )
        return clone_path

    logger.info("Cloning '%s' → '%s'", github_url, clone_path)

    try:
        git.Repo.clone_from(github_url, clone_path, depth=1)
    except git.GitCommandError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Git clone failed: {exc}"
        ) from exc

    return clone_path


def _collect_source_files(repo_path: str) -> list[dict]:
    """
    Walks the repo, reads every supported source file, and
    returns a list of dicts:
        file_path : absolute path
        rel_path  : path relative to repo root
        file_name : basename
        language  : language string
        content   : source code string
    """
    results = []

    for root, dirs, files in os.walk(repo_path):

        # Prune ignored directories in-place so os.walk skips them
        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS and not d.endswith(".egg-info")
        ]

        for filename in files:
            ext = Path(filename).suffix.lower()

            if ext not in SUPPORTED_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)

            # Skip over-large files
            try:
                if os.path.getsize(file_path) > MAX_FILE_BYTES:
                    logger.debug(
                        "Skipping large file: %s", file_path
                    )
                    continue
            except OSError:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except Exception as exc:
                logger.debug("Could not read %s: %s", file_path, exc)
                continue

            if not content.strip():
                continue

            results.append({
                "file_path": file_path,
                "rel_path":  os.path.relpath(file_path, repo_path),
                "file_name": filename,
                "language":  SUPPORTED_EXTENSIONS[ext],
                "content":   content,
            })

    return results


def _build_unified_graph(
    source_files: list[dict],
    repo_path: str
) -> tuple[dict, list[dict]]:
    """
    Builds a unified knowledge graph across all source files.

    Strategy:
      - Call build_repository_graph() for each file (it stores
        the graph in repository_graph_memory["active_graph"]).
      - After each call, extract nodes/edges and MERGE them into
        a single accumulator, annotating each node with its
        source file path.
      - The final merged graph is returned and stored as the
        new active_graph.

    Also builds and returns repository_index — the list of
    {file_name, rel_path, language, content} dicts consumed by
    RepositoryContextExpansionEngine.

    Returns: (unified_graph_dict, repository_index_list)
    """

    # ---- accumulator for merged graph ----
    merged_nodes: dict = {}
    merged_edges: list = []
    edge_set:     set  = set()  # dedup edges

    repository_index: list[dict] = []

    for file_info in source_files:
        content  = file_info["content"]
        rel_path = file_info["rel_path"]

        try:
            # build_repository_graph sets repository_graph_memory["active_graph"]
            file_graph = build_repository_graph(content)
        except Exception as exc:
            logger.warning(
                "Graph build failed for %s: %s — skipping.",
                rel_path, exc
            )
            continue

        # ---- merge nodes ----
        for node_id, node_data in file_graph.get("nodes", {}).items():

            if node_id not in merged_nodes:
                # First occurrence: store with file metadata
                merged_nodes[node_id] = node_data
                # Inject file path into metadata so cross-file
                # cognition engines can trace back to the source
                meta = merged_nodes[node_id].setdefault("metadata", {})
                if not meta.get("file_path"):
                    meta["file_path"] = rel_path
                    meta["file_name"] = file_info["file_name"]
            else:
                # Node seen in another file too — append file to
                # a "defined_in" list without overwriting first entry
                meta = merged_nodes[node_id].setdefault("metadata", {})
                defined_in = meta.setdefault("defined_in", [])
                if rel_path not in defined_in:
                    defined_in.append(rel_path)

        # ---- merge edges (deduplicated) ----
        for edge in file_graph.get("edges", []):
            edge_key = (
                edge.get("source", ""),
                edge.get("target", ""),
                edge.get("relationship", ""),
            )
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                merged_edges.append(edge)

        # ---- repository index entry ----
        repository_index.append({
            "file_name":   file_info["file_name"],
            "rel_path":    rel_path,
            "file_path":   file_info["file_path"],
            "language":    file_info["language"],
            "source_code": content,
        })

    # Preserve all extra keys from the last processed file graph
    # (inferred_types, symbol_table, etc.) but use merged nodes/edges
    last_graph = repository_graph_memory.get("active_graph", {})
    unified_graph = {**last_graph}
    unified_graph["nodes"] = merged_nodes
    unified_graph["edges"] = merged_edges

    return unified_graph, repository_index


def _embed_and_store(source_files: list[dict]) -> int:
    """
    Chunks each source file, embeds each chunk, and upserts
    into ChromaDB. Uses embedding_cache to skip re-embedding
    content seen before.

    Returns total number of chunks stored.
    """
    total_chunks = 0

    for file_info in source_files:
        content  = file_info["content"]
        rel_path = file_info["rel_path"]
        language = file_info["language"]

        try:
            chunks = universal_chunk_code(content)
        except Exception as exc:
            logger.debug(
                "Chunking failed for %s: %s", rel_path, exc
            )
            # Fallback: treat whole file as one chunk
            chunks = [{
                "chunk_id":   1,
                "language":   language,
                "type":       "file",
                "start_line": 1,
                "end_line":   content.count("\n") + 1,
                "content":    content[:MAX_FILE_BYTES],
            }]

        for chunk in chunks:
            chunk_content = chunk.get("content", "")

            if not chunk_content.strip():
                continue

            # ---- embed (with cache) ----
            cache_key = f"{rel_path}::{chunk_content}"

            if cache_key in embedding_cache:
                embedding = embedding_cache[cache_key]
            else:
                try:
                    embedding = embedding_model.encode(
                        chunk_content
                    ).tolist()
                    embedding_cache[cache_key] = embedding
                except Exception as exc:
                    logger.debug(
                        "Embedding failed for chunk in %s: %s",
                        rel_path, exc
                    )
                    continue

            # ---- upsert into ChromaDB ----
            chunk_id_str = (
                f"{rel_path}::{chunk.get('chunk_id', total_chunks)}"
            )

            try:
                collection.add(
                    ids=[chunk_id_str],
                    embeddings=[embedding],
                    documents=[chunk_content],
                    metadatas=[{
                        "file":       str(rel_path),
                        "language":   str(language),
                        "type":       str(chunk.get("type", "")),
                        "name":       str(chunk.get("name", "")),
                        "start_line": int(chunk.get("start_line") or 0),
                        "end_line":   int(chunk.get("end_line") or 0),
                    }]
                )
                total_chunks += 1

            except Exception as exc:
                # ChromaDB raises if the id already exists with
                # a different embedding — treat as non-fatal
                logger.debug(
                    "ChromaDB upsert error for chunk '%s': %s",
                    chunk_id_str, exc
                )

    return total_chunks