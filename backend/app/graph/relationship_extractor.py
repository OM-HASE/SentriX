import re

from app.intelligence.tree_sitter_engine import (
    detect_language
)


# ==========================================
# NORMALIZE FUNCTION CALL
# ==========================================

def normalize_function_call(
    text
):

    pattern = r"([a-zA-Z0-9_\.]+)\s*\("

    match = re.search(
        pattern,
        text
    )

    if not match:

        return None

    full_call = match.group(1)

    # ======================================
    # OBJECT + METHOD SPLIT
    # ======================================

    if "." in full_call:

        parts = full_call.split(".")

        object_name = ".".join(
            parts[:-1]
        )

        method_name = parts[-1]

    else:

        object_name = "global"

        method_name = full_call

    return {

        "type": "function_call",

        "object": object_name,

        "method": method_name,

        "signature": full_call
    }


# ==========================================
# IMPORT EXTRACTION
# ==========================================

def extract_imports(
    source_code
):

    imports = []

    patterns = [

        r"import\s+([a-zA-Z0-9_\.]+)",

        r"#include\s*[<\"](.+)[>\"]",

        r"using\s+namespace\s+([a-zA-Z0-9_]+)"
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            source_code
        )

        for match in matches:

            imports.append({

                "type": "import",

                "module": match
            })

    return imports


# ==========================================
# FUNCTION CALL EXTRACTION
# ==========================================

def extract_function_calls(
    source_code
):

    calls = []

    pattern = r"[a-zA-Z0-9_\.]+\s*\("

    matches = re.finditer(
        pattern,
        source_code
    )

    for match in matches:

        raw = match.group()

        normalized = normalize_function_call(
            raw
        )

        if normalized:

            calls.append(
                normalized
            )

    return calls


# ==========================================
# MAIN RELATIONSHIP EXTRACTION
# ==========================================

def extract_relationships(

    source_code,

    language=None
):

    if not language:

        language = detect_language(
            source_code
        )

    relationships = []

    # ======================================
    # IMPORTS
    # ======================================

    imports = extract_imports(
        source_code
    )

    relationships.extend(
        imports
    )

    # ======================================
    # FUNCTION CALLS
    # ======================================

    calls = extract_function_calls(
        source_code
    )

    relationships.extend(
        calls
    )

    return relationships