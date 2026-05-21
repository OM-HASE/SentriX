from __future__ import annotations

# =========================================
# SEMANTIC RERANKER
# =========================================
#
# BUG FIXED: The original reranker had this rule:
#
#   if "app" in meta.get("file", "").lower():
#       score += 2
#
# This is a hardcoded Flask-specific heuristic. Any repo whose
# main file isn't named "app.py" (Django's manage.py, Go's
# main.go, Rust's main.rs, etc.) gets unfairly ranked lower.
# This violates the architecture principle: the system must be
# language-agnostic and repository-driven, not framework-aware.
#
# Fix: All scoring is now purely semantic:
#   1. Filename relevance — does the filename appear in the
#      query? (e.g. query mentions "auth.py" → boost auth files)
#   2. Entity type boost — functions/classes are more
#      information-dense than loose statements.
#   3. Query token overlap — how many query words appear in
#      the document content? Normalized by query length so
#      long queries don't dominate short ones.
#
# None of these rules reference any specific framework,
# language, or file naming convention.
# =========================================


def rerank_results(
    query: str,
    results: dict
) -> list[dict]:
    """
    Re-ranks ChromaDB query results using semantic scoring.

    Args:
        query:   The original search query string.
        results: Raw ChromaDB query result dict with keys
                 'documents', 'metadatas', 'distances'.

    Returns:
        List of dicts, sorted by descending score, each with:
            score    — float, higher is more relevant
            document — the raw code/text chunk
            metadata — file, language, type, name, lines
    """

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        return []

    # Pre-tokenize query once — split on whitespace and
    # common punctuation, lowercase, drop empty tokens.
    query_tokens = set(
        token.strip("():.,\"'")
        for token in query.lower().split()
        if token.strip("():.,\"'")
    )

    query_token_count = max(len(query_tokens), 1)

    ranked = []

    for doc, meta, distance in zip(
        documents,
        metadatas,
        distances
    ):
        score = 0.0

        # ------------------------------------------
        # 1. VECTOR DISTANCE (always available)
        # ChromaDB returns L2 distance: lower = closer.
        # Convert to a 0-3 range so it contributes
        # proportionally alongside the other signals.
        # ------------------------------------------
        if distance is not None:
            score += max(0.0, 3.0 - float(distance))

        # ------------------------------------------
        # 2. ENTITY TYPE BOOST (language-agnostic)
        # Functions and classes contain the most
        # semantically dense code. Boost them slightly.
        # ------------------------------------------
        entity_type = meta.get("type", "")

        if entity_type in (
            "FunctionDef",
            "AsyncFunctionDef",
            "ClassDef",
            "function",
            "method",
            "class",
        ):
            score += 2.0

        # ------------------------------------------
        # 3. FILENAME RELEVANCE (repository-driven)
        # If the query explicitly mentions a filename
        # or module name that matches the chunk's source
        # file, this is a strong relevance signal.
        # e.g. query "error in auth.py login()" should
        # boost chunks from auth.py.
        # ------------------------------------------
        file_path = meta.get("file", "").lower()

        if file_path:
            # Check if any query token appears in the
            # file path (handles "auth", "auth.py",
            # "services/auth", etc.)
            for token in query_tokens:
                if token in file_path:
                    score += 2.0
                    break  # one match is enough

        # ------------------------------------------
        # 4. ENTITY NAME MATCH (symbol-level relevance)
        # If the function/class name in this chunk
        # appears directly in the query, it is highly
        # likely to be the code being investigated.
        # ------------------------------------------
        entity_name = meta.get("name", "").lower()

        if entity_name and entity_name in query.lower():
            score += 3.0

        # ------------------------------------------
        # 5. QUERY TOKEN OVERLAP IN CONTENT
        # Count how many unique query tokens appear in
        # the document. Normalize by query length so a
        # 50-word query doesn't dominate a 5-word one.
        # ------------------------------------------
        doc_lower = doc.lower()

        matching_tokens = sum(
            1
            for token in query_tokens
            if token in doc_lower
        )

        overlap_ratio = matching_tokens / query_token_count

        score += overlap_ratio * 4.0

        ranked.append({
            "score":    score,
            "document": doc,
            "metadata": meta,
        })

    # Sort descending by score, return all results.
    # Callers decide how many they want (top_k slicing
    # happens in retrieve_relevant_chunks).
    ranked.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked