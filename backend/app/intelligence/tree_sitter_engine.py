from tree_sitter import Language
from tree_sitter import Parser

import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_java
import tree_sitter_c
import tree_sitter_cpp
import tree_sitter_go
import tree_sitter_rust

import re
import ollama


# =========================================
# LANGUAGE MAP
# =========================================

LANGUAGE_MAP = {

    "python":
    Language(
        tree_sitter_python.language()
    ),

    "javascript":
    Language(
        tree_sitter_javascript.language()
    ),

    "java":
    Language(
        tree_sitter_java.language()
    ),

    "c":
    Language(
        tree_sitter_c.language()
    ),

    "cpp":
    Language(
        tree_sitter_cpp.language()
    ),

    "go":
    Language(
        tree_sitter_go.language()
    ),

    "rust":
    Language(
        tree_sitter_rust.language()
    )
}


# =========================================
# GET PARSER
# =========================================

def get_parser(
    language_name
):

    parser = Parser()

    parser.language = LANGUAGE_MAP[
        language_name
    ]

    return parser


# =========================================
# REGEX HEURISTIC DETECTION
# =========================================

def heuristic_language_detection(
    source_code
):

    code = source_code.lower()

    # =========================
    # PYTHON
    # =========================

    if re.search(
        r"\bdef\b|\bimport\b",
        code
    ):

        return "python"

    # =========================
    # JAVASCRIPT
    # =========================

    if re.search(
        r"console\.log|function|=>",
        code
    ):

        return "javascript"

    # =========================
    # JAVA
    # =========================

    if re.search(
        r"public class|system\.out\.println|import java",
        code
    ):

        return "java"

    # =========================
    # C++
    # =========================

    if re.search(
        r"#include|std::|cout",
        code
    ):

        return "cpp"

    # =========================
    # C
    # =========================

    if re.search(
        r"#include<stdio\.h>|printf",
        code
    ):

        return "c"

    # =========================
    # GO
    # =========================

    if re.search(
        r"package main|fmt\.print",
        code
    ):

        return "go"

    # =========================
    # RUST
    # =========================

    if re.search(
        r"fn main|println!",
        code
    ):

        return "rust"

    return "unknown"


# =========================================
# TREE-SITTER DETECTION
# =========================================

def tree_sitter_detection(
    source_code
):

    best_language = "unknown"

    best_score = -1

    for language_name in LANGUAGE_MAP.keys():

        try:

            parser = get_parser(
                language_name
            )

            tree = parser.parse(

                bytes(
                    source_code,
                    "utf8"
                )
            )

            root = tree.root_node

            score = len(
                root.children
            )

            if score > best_score:

                best_score = score

                best_language = language_name

        except Exception:

            continue

    return best_language


# =========================================
# LLM FALLBACK DETECTION
# =========================================

def llm_language_detection(
    source_code
):

    try:

        prompt = f"""
Detect the programming language.

Return ONLY one word.

CODE:
{source_code[:2000]}
"""

        response = ollama.chat(

            model="qwen2.5-coder:7b",

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            stream=False
        )

        language = response[
            "message"
        ]["content"].strip().lower()

        if language in LANGUAGE_MAP:

            return language

    except Exception:

        pass

    return "unknown"


# =========================================
# FINAL RESILIENT DETECTION
# =========================================

def detect_language(
    source_code
):

    # =====================================
    # HEURISTIC DETECTION
    # =====================================

    heuristic = heuristic_language_detection(
        source_code
    )

    if heuristic != "unknown":

        return heuristic

    # =====================================
    # TREE-SITTER DETECTION
    # =====================================

    tree_sitter_result = tree_sitter_detection(
        source_code
    )

    if tree_sitter_result != "unknown":

        return tree_sitter_result

    # =====================================
    # LLM DETECTION
    # =====================================

    llm_result = llm_language_detection(
        source_code
    )

    if llm_result != "unknown":

        return llm_result

    # =====================================
    # FINAL FALLBACK
    # =====================================

    return "python"


# =========================================
# EXTRACT FUNCTIONS + CLASSES
# =========================================

def extract_functions_and_classes(

    source_code,

    language=None
):

    # =====================================
    # AUTO DETECT
    # =====================================

    if not language:

        language = detect_language(
            source_code
        )

    language = language.lower()

    # =====================================
    # SAFETY FALLBACK
    # =====================================

    if language not in LANGUAGE_MAP:

        language = "python"

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

    results = []

    FUNCTION_NODES = {

        "python": [

            "function_definition",

            "class_definition"
        ],

        "javascript": [

            "function_declaration",

            "class_declaration",

            "method_definition"
        ],

        "java": [

            "class_declaration",

            "method_declaration"
        ],

        "cpp": [

            "function_definition",

            "class_specifier"
        ],

        "c": [

            "function_definition"
        ],

        "go": [

            "function_declaration",

            "method_declaration"
        ],

        "rust": [

            "function_item",

            "struct_item",

            "impl_item"
        ]
    }

    target_nodes = FUNCTION_NODES.get(
        language,
        []
    )

    def traverse(node):

        if node.type in target_nodes:

            entity_name = "unknown_entity"

            try:

                for child in node.children:

                    if child.type == "identifier":

                        entity_name = source_code[

                            child.start_byte:
                            child.end_byte
                        ]

                        break

            except Exception:

                pass

            results.append({

                "entity_name":
                entity_name,

                "type":
                node.type,

                "start_line":
                node.start_point[0] + 1,

                "end_line":
                node.end_point[0] + 1,

                "text":
                source_code[
                    node.start_byte:
                    node.end_byte
                ]
            })

        for child in node.children:

            traverse(child)

    traverse(root)

    return results