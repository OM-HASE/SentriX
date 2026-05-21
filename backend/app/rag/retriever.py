from __future__ import annotations
import logging
 
from app.rag.embeddings import embedding_model
from app.rag.vector_store import collection
from app.rag.reranker import rerank_results
 
logger = logging.getLogger(__name__)
 
# =========================================
# RETRIEVE RELEVANT CHUNKS
# =========================================
#
# BUG FIXED: The original code had no guard for an empty
# ChromaDB collection. When no repository has been ingested
# yet (fresh install, or chroma_db wiped), collection.query()
# raises:
#
#   chromadb.errors.InvalidArgumentError:
#   Number of requested results N is greater than number
#   of elements in index M, can't search.
#
# This crash propagated all the way up through graph_rca_agent
# and returned a 500 to the caller with no explanation.
#
# Fix: Check collection.count() before querying. If the
# collection is empty, return an empty list immediately
# with a log warning. The RCA pipeline handles [] gracefully
# (it skips enriched context and proceeds with graph-only
# reasoning — still useful output).
#
# RETURN FORMAT (normalized for all consumers):
#   list[dict] where each dict has:
#       score    : float — relevance score from reranker
#       document : str   — raw code/text chunk
#       metadata : dict  — file, language, type, name, lines
#
# Both rca_agent.py and graph_rca_agent.py consume this
# format correctly:
#   rca_agent       → [item["document"] for item in results]
#   graph_rca_agent → passes list to build_enriched_context()
#                     (fixed in enriched_context_builder.py)
# =========================================
 
 
def retrieve_relevant_chunks(
    query: str,
    top_k: int = 3
) -> list[dict]:
    """
    Embeds the query and retrieves the top_k most relevant
    code chunks from ChromaDB, re-ranked semantically.
 
    Returns an empty list (never raises) if:
      - The collection has no documents yet
      - Embedding fails
      - ChromaDB query fails
 
    Each returned dict:
        score    : float  — higher = more relevant
        document : str    — the code/text chunk
        metadata : dict   — file, language, type, name, lines
    """
 
    # --------------------------------------------------
    # GUARD: empty collection
    # --------------------------------------------------
    try:
        doc_count = collection.count()
    except Exception as exc:
        logger.warning(
            "Could not read ChromaDB collection count: %s. "
            "Returning empty context — RCA will proceed "
            "with graph-only reasoning.",
            exc
        )
        return []
 
    if doc_count == 0:
        logger.warning(
            "ChromaDB collection is empty. "
            "No repository has been ingested yet. "
            "Call POST /api/process-repo first. "
            "Returning empty context."
        )
        return []
 
    # --------------------------------------------------
    # EMBED QUERY
    # --------------------------------------------------
    try:
        query_embedding = embedding_model.encode(
            query
        ).tolist()
    except Exception as exc:
        logger.warning(
            "Embedding model failed on query: %s. "
            "Returning empty context.",
            exc
        )
        return []
 
    # --------------------------------------------------
    # CHROMADB QUERY
    # Clamp top_k to available documents so ChromaDB
    # doesn't raise "requested more results than index size".
    # --------------------------------------------------
    safe_top_k = min(top_k, doc_count)
 
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=safe_top_k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as exc:
        logger.warning(
            "ChromaDB query failed: %s. "
            "Returning empty context.",
            exc
        )
        return []
 
    # --------------------------------------------------
    # RERANK AND RETURN
    # --------------------------------------------------
    reranked = rerank_results(query, results)
 
    return reranked