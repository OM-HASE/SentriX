from app.intelligence.tree_sitter_engine import (
    get_parser,
    detect_language
)

# ==========================================
# NODE TYPE MAP
# ==========================================

CALL_NODE_TYPES = {

    "python": [

        "call",
        "attribute",
        "ERROR"
    ],

    "javascript": [

        "call_expression",
        "member_expression",
        "ERROR"
    ],

    "java": [

        "method_invocation",
        "field_access",
        "ERROR"
    ],

    "cpp": [

        "call_expression",
        "field_expression",
        "ERROR"
    ],

    "c": [

        "call_expression",
        "field_expression",
        "ERROR"
    ],

    "go": [

        "call_expression",
        "selector_expression",
        "ERROR"
    ],

    "rust": [

        "call_expression",
        "field_expression",
        "ERROR"
    ]
}


IMPORT_NODE_TYPES = {

    "python": [

        "import_statement",
        "import_from_statement"
    ],

    "javascript": [

        "import_statement"
    ],

    "java": [

        "import_declaration"
    ],

    "cpp": [

        "preproc_include"
    ],

    "c": [

        "preproc_include"
    ],

    "go": [

        "import_declaration"
    ],

    "rust": [

        "use_declaration"
    ]
}


# ==========================================
# TEXT EXTRACTION
# ==========================================

def get_node_text(

    source_code,

    node
):

    return source_code[
        node.start_byte:
        node.end_byte
    ]


# ==========================================
# VALID SEMANTIC TOKEN
# ==========================================

def is_valid_semantic_token(

    value
):

    if not value:

        return False

    if not isinstance(
        value,
        str
    ):

        return False

    cleaned = value.strip()

    if not cleaned:

        return False

    if len(cleaned) > 100:

        return False

    if "\n" in cleaned:

        return False

    invalid_exact_tokens = {

        ":",
        "+",
        "-",
        "*",
        "/",
        "=",
        "==",
        "!=",
        ">",
        "<",
        ">=",
        "<=",
        "&&",
        "||"
    }

    if cleaned in invalid_exact_tokens:

        return False

    invalid_prefixes = [

        "(",
        "{",
        "[",
        ",",
        ";"
    ]

    for prefix in invalid_prefixes:

        if cleaned.startswith(
            prefix
        ):

            return False

    return True


# ==========================================
# NORMALIZE INVOCATION TEXT
# ==========================================

def normalize_invocation_text(

    raw_text
):

    if not raw_text:

        return ""

    raw_text = (
        raw_text
        .replace("\n", " ")
        .replace("\t", " ")
        .strip()
    )

    raw_text = " ".join(
        raw_text.split()
    )

    # ======================================
    # REMOVE PARAMETERS
    # ======================================

    if "(" in raw_text:

        raw_text = (
            raw_text
            .split("(")[0]
            .strip()
        )

    # ======================================
    # REMOVE ASSIGNMENTS
    # ======================================

    if "=" in raw_text:

        raw_text = (
            raw_text
            .split("=")[-1]
            .strip()
        )

    # ======================================
    # REMOVE GENERICS
    # ======================================

    if ">" in raw_text:

        raw_text = (
            raw_text
            .split(">")[-1]
            .strip()
        )

    # ======================================
    # REMOVE SEMICOLONS
    # ======================================

    raw_text = raw_text.replace(
        ";",
        ""
    )

    # ======================================
    # REMOVE RETURN
    # ======================================

    if raw_text.startswith(
        "return "
    ):

        raw_text = (
            raw_text.replace(
                "return ",
                ""
            )
        )

    # ======================================
    # REMOVE TYPE PREFIXES
    # ======================================

    tokens = raw_text.split()

    if len(tokens) > 1:

        raw_text = tokens[-1]

    return raw_text.strip()


# ==========================================
# BUILD RELATIONSHIP
# ==========================================

def build_relationship(

    invocation_text
):

    try:

        if not invocation_text:

            return None

        if "." not in invocation_text:

            if not is_valid_semantic_token(
                invocation_text
            ):

                return None

            return {

                "relationship_type":
                "calls",

                "object":
                "global",

                "method":
                invocation_text,

                "signature":
                invocation_text,

                "source_type":
                "semantic_invocation"
            }

        parts = [

            p.strip()

            for p in invocation_text.split(".")

            if p.strip()
        ]

        if len(parts) < 2:

            return None

        object_name = ".".join(
            parts[:-1]
        )

        method_name = parts[-1]

        if not is_valid_semantic_token(
            object_name
        ):

            return None

        if not is_valid_semantic_token(
            method_name
        ):

            return None

        return {

            "relationship_type":
            "calls",

            "object":
            object_name,

            "method":
            method_name,

            "signature":
            f"{object_name}.{method_name}",

            "source_type":
            "semantic_invocation"
        }

    except Exception:

        return None


# ==========================================
# EXTRACT INVOCATION COMPONENTS
# ==========================================

def extract_invocation_components(

    node,

    source_code
):

    try:

        raw_text = source_code[
            node.start_byte:
            node.end_byte
        ].strip()

        if not raw_text:

            return None

        invocation_text = (
            normalize_invocation_text(
                raw_text
            )
        )

        return build_relationship(
            invocation_text
        )

    except Exception:

        return None


# ==========================================
# SEMANTIC RECONSTRUCTION
# ==========================================

def reconstruct_semantic_invocation(

    node,

    source_code
):

    try:

        raw_text = source_code[
            node.start_byte:
            node.end_byte
        ].strip()

        if not raw_text:

            return None

        invocation_text = (
            normalize_invocation_text(
                raw_text
            )
        )

        return build_relationship(
            invocation_text
        )

    except Exception:

        return None


# ==========================================
# RAW SOURCE INVOCATION SCAN
# ==========================================

def scan_raw_source_invocations(

    source_code
):

    relationships = []

    visited = set()

    lines = source_code.splitlines()

    for line in lines:

        stripped = line.strip()

        if not stripped:

            continue

        if "." not in stripped:

            continue

        if "(" not in stripped:

            continue

        invocation_text = (
            normalize_invocation_text(
                stripped
            )
        )

        relationship = build_relationship(
            invocation_text
        )

        if not relationship:

            continue

        signature = relationship.get(
            "signature"
        )

        if signature in visited:

            continue

        visited.add(signature)

        relationships.append(
            relationship
        )

    return relationships


# ==========================================
# FUNCTION CALL EXTRACTION
# ==========================================

def extract_function_calls(

    source_code,

    root,

    language
):

    relationships = []

    visited_signatures = set()

    target_nodes = CALL_NODE_TYPES.get(
        language,
        []
    )

    # ======================================
    # TREE TRAVERSAL
    # ======================================

    def traverse(node):

        if node.type in target_nodes:

            # ==============================
            # DIRECT EXTRACTION
            # ==============================

            relationship = (

                extract_invocation_components(

                    node,

                    source_code
                )
            )

            # ==============================
            # FALLBACK RECONSTRUCTION
            # ==============================

            if not relationship:

                relationship = (

                    reconstruct_semantic_invocation(

                        node,

                        source_code
                    )
                )

            # ==============================
            # ADD RELATIONSHIP
            # ==============================

            if relationship:

                signature = relationship.get(
                    "signature"
                )

                if (

                    signature
                    and
                    signature not in visited_signatures

                ):

                    visited_signatures.add(
                        signature
                    )

                    relationships.append(
                        relationship
                    )

        for child in node.children:

            traverse(child)

    traverse(root)

    return relationships


# ==========================================
# IMPORT EXTRACTION
# ==========================================

def extract_imports(

    source_code,

    root,

    language
):

    imports = []

    target_nodes = IMPORT_NODE_TYPES.get(
        language,
        []
    )

    def traverse(node):

        if node.type in target_nodes:

            import_text = get_node_text(
                source_code,
                node
            ).strip()

            if not import_text:

                return

            imports.append({

                "relationship_type":
                "imports",

                "module":
                import_text
            })

        for child in node.children:

            traverse(child)

    traverse(root)

    return imports


# ==========================================
# MAIN SEMANTIC EXTRACTION
# ==========================================

def extract_semantic_relationships(

    source_code,

    language=None
):

    if not language:

        language = detect_language(
            source_code
        )

    language = language.lower()

    parser = get_parser(
        language
    )

    tree = parser.parse(

        bytes(
            source_code,
            "utf8"
        )
    )

    root = tree.root_node

    relationships = []

    # ======================================
    # IMPORTS
    # ======================================

    imports = extract_imports(

        source_code,

        root,

        language
    )

    relationships.extend(
        imports
    )

    # ======================================
    # AST EXTRACTION
    # ======================================

    calls = extract_function_calls(

        source_code,

        root,

        language
    )

    relationships.extend(
        calls
    )

    # ======================================
    # RAW SOURCE FALLBACK
    # ======================================

    raw_scan_relationships = (

        scan_raw_source_invocations(
            source_code
        )
    )

    existing_signatures = {

        item.get("signature")

        for item in relationships
    }

    for relationship in raw_scan_relationships:

        signature = relationship.get(
            "signature"
        )

        if signature not in existing_signatures:

            relationships.append(
                relationship
            )

    return relationships