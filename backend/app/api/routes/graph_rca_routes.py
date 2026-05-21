from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.graph_rca_agent import analyze_graph_root_cause
from app.graph.graph_builder import build_repository_graph
from app.graph.graph_memory import repository_graph_memory
from app.services.persistence_service import get_memory_status
from app.intelligence.language_detector import detect_language

logger = logging.getLogger(__name__)

router = APIRouter()

# ==========================================
# ANALYSIS MODES
# ==========================================
#
# code_only        → source code submitted, no error log
#                    → static analysis only, no LLM reasoning
# code_and_logs    → source code + error log submitted
#                    → build graph from code, then full RCA
# logs_only        → only error log submitted
#                    → requires pre-ingested repo in memory
#                    → full RCA using active graph
#
# If no repo is ingested and logs_only is requested → 409


# ==========================================
# SCHEMAS
# ==========================================

class GraphRCARequest(BaseModel):
    error_log   : str
    source_code : str


class RCARequest(BaseModel):
    """
    Primary RCA endpoint.

    Submit:
      - error_log only      → uses pre-ingested repo graph
      - error_log + code    → merges code into graph then RCA
      - source_code only    → static graph analysis, no RCA
    """
    error_log   : str | None = None
    source_code : str | None = None


# ==========================================
# ORIGINAL ROUTE  (backward compat)
# ==========================================

@router.post("/graph-rca")
async def graph_rca(data: GraphRCARequest):
    build_repository_graph(data.source_code)
    result = analyze_graph_root_cause(
        error_log   = data.error_log,
        source_code = data.source_code,
    )
    return {"graph_rca": result}


# ==========================================
# PRIMARY RCA ROUTE
# ==========================================

@router.post("/rca")
async def rca(data: RCARequest):
    """
    Primary RCA endpoint — auto-detects mode from input.

    Modes:
      logs_only     → only error_log provided
      code_and_logs → both provided
      code_only     → only source_code provided

    logs_only requires a repository to be ingested first via
    POST /api/ingest-repo or /api/ingest-code.
    """

    has_log  = bool(data.error_log  and data.error_log.strip())
    has_code = bool(data.source_code and data.source_code.strip())

    if not has_log and not has_code:
        raise HTTPException(
            status_code=422,
            detail="Provide at least error_log or source_code."
        )

    # ---- detect mode ----
    if has_log and has_code:
        mode = "code_and_logs"
    elif has_log:
        mode = "logs_only"
    else:
        mode = "code_only"

    logger.info("RCA mode: %s", mode)

    # ---- detect language ----
    language = "unknown"
    if has_code:
        try:
            language = detect_language(data.source_code)
        except Exception:
            pass

    # ---- logs_only: require ingested graph ----
    if mode == "logs_only":
        active_graph = repository_graph_memory.get("active_graph", {})
        if not active_graph or not active_graph.get("nodes"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Mode 'logs_only' requires a repository to be ingested. "
                    "Call POST /api/ingest-code or /api/ingest-repo first, "
                    "then retry."
                )
            )

    # ---- code_and_logs / code_only: MERGE code into graph ----
    # Critical fix: we MERGE instead of replace so the full
    # ingested multi-file graph is preserved and the submitted
    # snippet just adds extra context nodes.
    if has_code:
        _merge_code_into_graph(data.source_code)

    # ---- code_only: return graph analysis without LLM RCA ----
    if mode == "code_only":
        active_graph = repository_graph_memory.get("active_graph", {})
        nodes = active_graph.get("nodes", {})
        edges = active_graph.get("edges", [])
        return {
            "mode":     mode,
            "language": language,
            "analysis": {
                "graph_node_count": len(nodes),
                "graph_edge_count": len(edges),
                "entities": [
                    {"name": nid, "type": nd.get("type")}
                    for nid, nd in list(nodes.items())[:50]
                ],
                "message": (
                    "Static graph built. Provide error_log to run full RCA."
                )
            }
        }

    # ---- code_and_logs / logs_only: full RCA ----
    result = analyze_graph_root_cause(
        error_log   = data.error_log or "",
        source_code = data.source_code or "",
    )

    return {
        "mode":     mode,
        "language": language if has_code else result.get("stack_trace_mapping", {}).get("language", "unknown"),
        "rca":      result,
    }


# ==========================================
# STATUS ROUTE
# ==========================================

@router.get("/status")
def status():
    mem   = get_memory_status()
    ready = mem["graph_node_count"] > 0
    return {
        "ready":   ready,
        "message": (
            f"Graph loaded: {mem['repo_name']} "
            f"({mem['graph_node_count']} nodes, "
            f"{mem['indexed_files']} files indexed)"
            if ready
            else "No repository ingested. Call POST /api/ingest-code."
        ),
        **mem,
    }


# ==========================================
# MERGE HELPER
# ==========================================

def _merge_code_into_graph(source_code: str):
    """
    Builds a graph from source_code and MERGES its nodes/edges
    into repository_graph_memory["active_graph"] without
    overwriting the existing graph.

    This preserves the full multi-file graph from ingest
    while adding extra context from the submitted snippet.
    """
    try:
        new_graph = build_repository_graph(source_code)
    except Exception as exc:
        logger.warning("Graph build for snippet failed: %s", exc)
        return

    active = repository_graph_memory.get("active_graph", {})

    if not active or not active.get("nodes"):
        # Nothing ingested yet — use the new graph as-is
        return

    # Merge nodes (new graph was already stored by build_repository_graph,
    # but that OVERWROTE active_graph — restore the merged version)
    merged_nodes = dict(active.get("nodes", {}))
    for node_id, node_data in new_graph.get("nodes", {}).items():
        if node_id not in merged_nodes:
            merged_nodes[node_id] = node_data

    merged_edges = list(active.get("edges", []))
    edge_set = {
        (e.get("source"), e.get("target"), e.get("relationship"))
        for e in merged_edges
        if e.get("source") and e.get("target")
    }
    for edge in new_graph.get("edges", []):
        key = (edge.get("source"), edge.get("target"), edge.get("relationship"))
        if key[0] and key[1] and key not in edge_set:
            edge_set.add(key)
            merged_edges.append(edge)

    # Restore merged graph into memory
    merged = {**new_graph}
    merged["nodes"] = merged_nodes
    merged["edges"] = merged_edges
    repository_graph_memory["active_graph"] = merged