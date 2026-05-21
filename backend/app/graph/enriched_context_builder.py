from __future__ import annotations
 
from app.graph.graph_retriever import (
    retrieve_graph_neighbors
)

def build_enriched_context(
    retrieved_chunks: list
) -> list:
    """
    Takes retrieved chunks (list of dicts OR strings) and
    enriches each one with its graph neighbors from the
    in-memory repository knowledge graph.
 
    Args:
        retrieved_chunks: Output from retrieve_relevant_chunks().
            Each element is either:
              - dict with keys: score, document, metadata
              - str (plain code text, fallback path)
 
    Returns:
        List mixing raw chunk entries and graph-neighbor dicts.
        Passed as context to LLM reasoning in graph_rca_agent.
    """
 
    enriched_context = []
 
    for chunk in retrieved_chunks:
 
        # --------------------------------------------------
        # NORMALIZE: dict → text string
        # --------------------------------------------------
        if isinstance(chunk, dict):
            chunk_text = chunk.get("document", "")
            chunk_meta = chunk.get("metadata", {})
        else:
            # Defensive: handle plain strings if this
            # function is ever called from another path.
            chunk_text = str(chunk)
            chunk_meta = {}
 
        if not chunk_text:
            continue
 
        # Include the original chunk entry as-is
        enriched_context.append(chunk)
 
        # --------------------------------------------------
        # GRAPH ENRICHMENT
        # Extract the entity name from the chunk text so we
        # can pull its neighbors from the knowledge graph.
        #
        # Priority order:
        #   1. metadata["name"] — exact name from AST parser
        #   2. "def <name>(" pattern in source text
        #   3. "class <name>:" pattern in source text
        #
        # Using metadata first is more reliable than regex
        # on source text (handles multi-line signatures,
        # decorators, etc.)
        # --------------------------------------------------
        entity_name = (
            chunk_meta.get("name")
            or _extract_entity_name(chunk_text)
        )
 
        if entity_name:
            neighbors = retrieve_graph_neighbors(entity_name)
 
            if neighbors:
                enriched_context.append({
                    "entity":          entity_name,
                    "graph_neighbors": neighbors,
                    "source_file":     chunk_meta.get("file", ""),
                })
 
    return enriched_context
 
 
def _extract_entity_name(
    chunk_text: str
) -> str | None:
    """
    Heuristically extracts the primary entity name from a
    code chunk when metadata doesn't provide it.
 
    Returns the first function or class name found, or None.
    """
 
    for line in chunk_text.splitlines():
        stripped = line.strip()
 
        if stripped.startswith("def "):
            # "def my_function(args):" → "my_function"
            try:
                return stripped.split("def ")[1].split("(")[0].strip()
            except IndexError:
                pass
 
        if stripped.startswith("class "):
            # "class MyClass(Base):" → "MyClass"
            try:
                return (
                    stripped
                    .split("class ")[1]
                    .split("(")[0]
                    .split(":")[0]
                    .strip()
                )
            except IndexError:
                pass
 
    return None