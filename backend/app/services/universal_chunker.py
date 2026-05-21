from app.intelligence.tree_sitter_engine import (
    detect_language,
    extract_functions_and_classes
)


def universal_chunk_code(
    source_code
):

    language = detect_language(
        source_code
    )

    if language == "Unknown":

        return []

    chunks = extract_functions_and_classes(

        source_code,

        language=language.lower()
    )

    structured_chunks = []

    for idx, chunk in enumerate(chunks):

        structured_chunks.append({

            "chunk_id": idx + 1,

            "language": language,

            "type": chunk["type"],

            "start_line":
            chunk["start_line"],

            "end_line":
            chunk["end_line"],

            "content":
            chunk["text"]
        })

    return structured_chunks