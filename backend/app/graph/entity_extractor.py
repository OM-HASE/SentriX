from app.intelligence.tree_sitter_engine import (
    extract_functions_and_classes,
    detect_language
)


# ==========================================
# CLEAN ENTITY NAME
# ==========================================

def clean_entity_name(

    name
):

    if not name:

        return None

    cleaned = str(name).strip()

    removable_tokens = [

        "{",
        "}",
        "(",
        ")",
        ";",
        ",",
        ":"
    ]

    for token in removable_tokens:

        cleaned = cleaned.replace(
            token,
            ""
        )

    cleaned = cleaned.strip()

    if len(cleaned) <= 1:

        return None

    return cleaned


# ==========================================
# EXTRACT CODE ENTITIES
# ==========================================

def extract_code_entities(

    source_code
):

    language = detect_language(
        source_code
    )

    chunks = extract_functions_and_classes(

        source_code,

        language=language.lower()
    )

    entities = []

    # ======================================
    # TREE-SITTER ENTITY NORMALIZATION
    # ======================================

    for chunk in chunks:

        metadata = chunk.get(
            "metadata",
            {}
        )

        entity_name = (

            metadata.get(
                "name"
            )

            or

            metadata.get(
                "identifier"
            )

            or

            metadata.get(
                "function_name"
            )

            or

            metadata.get(
                "class_name"
            )
        )

        entity_name = clean_entity_name(
            entity_name
        )

        # ==================================
        # INVALID ENTITY
        # ==================================

        if not entity_name:

            continue

        entities.append({

            "entity_name":
            entity_name,

            "entity_type":
            chunk.get(
                "type",
                "unknown"
            ),

            "start_line":
            chunk.get(
                "start_line"
            ),

            "end_line":
            chunk.get(
                "end_line"
            ),

            "content":
            chunk.get(
                "text",
                ""
            ),

            "metadata":
            metadata,

            "parent":
            None
        })

    return entities