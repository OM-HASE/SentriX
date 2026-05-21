from __future__ import annotations

import json
import os
import logging
from pathlib import Path

from app.graph.graph_memory import repository_graph_memory

logger = logging.getLogger(__name__)

# =========================================
# STORAGE PATH
# =========================================
# Stored next to chroma_db so everything
# repo-related lives in one place.

PERSISTENCE_DIR  = "./sentrix_memory"
GRAPH_STATE_FILE = os.path.join(PERSISTENCE_DIR, "repository_graph_state.json")

os.makedirs(PERSISTENCE_DIR, exist_ok=True)


# =========================================
# SAVE
# =========================================

def save_graph_memory() -> bool:
    """
    Serializes repository_graph_memory to disk.

    Called automatically by ingest_routes after a successful
    ingestion so the graph survives server restarts.

    Returns True on success, False on error (non-fatal — the
    system continues working, just won't persist across restarts).
    """
    try:
        # repository_graph_memory may contain sets (language
        # detection) which aren't JSON-serializable. Convert them.
        serializable = _make_serializable(
            dict(repository_graph_memory)
        )

        with open(GRAPH_STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2)

        size_kb = Path(GRAPH_STATE_FILE).stat().st_size // 1024
        logger.info(
            "Graph memory saved to '%s' (%d KB).",
            GRAPH_STATE_FILE, size_kb
        )
        return True

    except Exception as exc:
        logger.warning(
            "Could not save graph memory: %s — "
            "data will be lost on restart.",
            exc
        )
        return False


# =========================================
# LOAD
# =========================================

def load_graph_memory() -> bool:
    """
    Loads previously saved graph memory from disk into
    repository_graph_memory.

    Called once during FastAPI startup. If the file doesn't
    exist (fresh install) or is corrupt, returns False and
    the system starts with an empty graph — not a crash.

    Returns True if memory was loaded, False otherwise.
    """
    if not os.path.exists(GRAPH_STATE_FILE):
        logger.info(
            "No persisted graph state found at '%s'. "
            "Starting fresh — call POST /api/ingest-repo first.",
            GRAPH_STATE_FILE
        )
        return False

    try:
        with open(GRAPH_STATE_FILE, "r", encoding="utf-8") as fh:
            state = json.load(fh)

        repository_graph_memory.clear()
        repository_graph_memory.update(state)

        node_count = len(
            repository_graph_memory
            .get("active_graph", {})
            .get("nodes", {})
        )
        repo_name = repository_graph_memory.get("repo_name", "unknown")

        logger.info(
            "Graph memory loaded from '%s'. "
            "Repo: '%s', %d graph nodes.",
            GRAPH_STATE_FILE, repo_name, node_count
        )
        return True

    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning(
            "Persisted graph state at '%s' is corrupt: %s. "
            "Starting fresh.",
            GRAPH_STATE_FILE, exc
        )
        return False

    except Exception as exc:
        logger.warning(
            "Could not load graph memory: %s. Starting fresh.",
            exc
        )
        return False


# =========================================
# STATUS
# =========================================

def get_memory_status() -> dict:
    """
    Returns a dict summarising what's currently in memory.
    Used by the /api/status route.
    """
    active_graph = repository_graph_memory.get("active_graph", {})
    repo_index   = repository_graph_memory.get("repository_index", [])

    return {
        "repo_name":        repository_graph_memory.get("repo_name", None),
        "repo_path":        repository_graph_memory.get("repo_path", None),
        "graph_node_count": len(active_graph.get("nodes", {})),
        "graph_edge_count": len(active_graph.get("edges", [])),
        "indexed_files":    len(repo_index),
        "persisted_state":  os.path.exists(GRAPH_STATE_FILE),
        "memory_file":      GRAPH_STATE_FILE,
    }


# =========================================
# HELPERS
# =========================================

def _make_serializable(obj):
    """
    Recursively converts non-JSON-serializable types:
      set  → sorted list
      any other non-serializable → str(obj)
    """
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(_make_serializable(v) for v in obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    # Fallback for anything else (e.g. custom objects)
    try:
        return str(obj)
    except Exception:
        return None