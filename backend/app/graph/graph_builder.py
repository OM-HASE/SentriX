from app.graph.knowledge_graph import (
    RepositoryKnowledgeGraph
)

from app.graph.entity_extractor import (
    extract_code_entities
)

from app.graph.semantic_relationship_extractor import (
    extract_semantic_relationships
)

from app.graph.semantic_edge_engine import (
    build_semantic_edges
)

from app.intelligence.tree_sitter_engine import (
    detect_language
)

from app.graph.graph_memory import (
    repository_graph_memory
)

import logging
logger = logging.getLogger(__name__)

from app.cognition.type_inference_engine import (
    TypeInferenceEngine
)

from app.cognition.repository_symbol_table import (
    RepositorySymbolTable
)

from app.cognition.method_compatibility_engine import (
    MethodCompatibilityEngine
)

from app.cognition.symbol_resolution_engine import (
    SymbolResolutionEngine
)


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

    # ======================================
    # EMPTY
    # ======================================

    if not cleaned:

        return False

    # ======================================
    # VERY LARGE TOKENS
    # ======================================

    if len(cleaned) > 80:

        return False

    # ======================================
    # MULTILINE GARBAGE
    # ======================================

    if "\n" in cleaned:

        return False

    # ======================================
    # EXCESSIVE WHITESPACE
    # ======================================

    if len(cleaned.split()) > 4:

        return False

    # ======================================
    # INVALID EXACT TOKENS
    # ======================================

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
        "||",
        ".."
    }

    if cleaned in invalid_exact_tokens:

        return False

    # ======================================
    # INVALID PREFIX
    # ======================================

    invalid_prefixes = [

        "(",
        "{",
        "[",
        ".",
        ","
    ]

    for prefix in invalid_prefixes:

        if cleaned.startswith(
            prefix
        ):

            return False

    # ======================================
    # INVALID BLOCK-LIKE CONTENT
    # ======================================

    invalid_fragments = [

        "{",
        "}",
        ";",
        "=>",
        "return ",
        "\t"
    ]

    invalid_count = 0

    for fragment in invalid_fragments:

        if fragment in cleaned:

            invalid_count += 1

    if invalid_count >= 2:

        return False

    # ======================================
    # EXCESSIVE BRACKETS
    # ======================================

    bracket_count = (

        cleaned.count("(")
        +
        cleaned.count("{")
        +
        cleaned.count("[")
    )

    if bracket_count >= 2:

        return False

    # ======================================
    # EXCESSIVE DOT CHAIN
    # ======================================

    if cleaned.count(".") > 2:

        return False

    return True


# =========================================================
# BUILD REPOSITORY GRAPH
# =========================================================

def build_repository_graph(source_code):

    # =====================================================
    # INITIALIZE GRAPH
    # =====================================================

    graph = RepositoryKnowledgeGraph()

    graph.add_node(
        node_id="source_code",
        node_type="raw_source",
        metadata={
            "source_code": source_code,
            "synthetic": True
        }
    )

    graph.add_node(
        node_id="repository",
        node_type="repository_root",
        metadata={
            "synthetic": True
        }
    )

    # =====================================================
    # DETECT LANGUAGE
    # =====================================================

    language = detect_language(
        source_code
    ).lower()

    # =====================================================
    # ENTITY EXTRACTION
    # =====================================================

    entities = extract_code_entities(
        source_code
    )

    for entity in entities:

        node_id = entity.get(
            "entity_name"
        )

        if not is_valid_semantic_token(
            node_id
        ):
            continue

        graph.add_node(

            node_id=node_id,

            node_type=entity.get(
                "entity_type",
                "unknown"
            ),

            metadata=entity
        )

    # =====================================================
    # RELATIONSHIP EXTRACTION
    # =====================================================

    relationships = extract_semantic_relationships(

        source_code,

        language=language
    )

    for relation in relationships:

        relation_type = relation.get(
            "relationship_type",
            "unknown"
        )

        # =================================================
        # FUNCTION CALL RELATIONSHIPS
        # =================================================

        if relation_type == "calls":

            caller = relation.get(
                "caller"
            )

            callee = relation.get(
                "callee"
            )

            relation_node = relation.get(
                "signature",
                "unknown_call"
            )

            # =============================================
            # SANITIZATION
            # =============================================

            if not is_valid_semantic_token(
                caller
            ):
                continue

            if not is_valid_semantic_token(
                callee
            ):
                continue

            # =============================================
            # ADD CALL NODE
            # =============================================

            if is_valid_semantic_token(
                relation_node
            ):

                graph.add_node(

                    node_id=relation_node,

                    node_type="calls",

                    metadata=relation
                )

            # =============================================
            # ADD CALL EDGE
            # =============================================

            graph.add_edge(

                source=caller,

                target=callee,

                relationship="calls"
            )

            continue

        # =================================================
        # IMPORT RELATIONSHIPS
        # =================================================

        elif relation_type == "imports":

            relation_node = relation.get(
                "module",
                "unknown_import"
            )

        # =================================================
        # FALLBACK RELATIONSHIPS
        # =================================================

        else:

            relation_node = str(
                relation
            )

        # =================================================
        # SANITIZATION
        # =================================================

        if not is_valid_semantic_token(
            relation_node
        ):
            continue

        # =================================================
        # ADD RELATION NODE
        # =================================================

        graph.add_node(

            node_id=relation_node,

            node_type=relation_type,

            metadata=relation
        )

    # =====================================================
    # BUILD SEMANTIC EDGES
    # =====================================================

    semantic_edges = build_semantic_edges(

        entities,

        relationships
    )

    for edge in semantic_edges:

        source = edge.get(
            "source"
        )

        target = edge.get(
            "target"
        )

        # =================================================
        # SANITIZATION
        # =================================================

        if not is_valid_semantic_token(
            source
        ):
            continue

        if not is_valid_semantic_token(
            target
        ):
            continue

        graph.add_edge(

            source=source,

            target=target,

            relationship=edge.get(
                "relationship"
            )
        )

    # =====================================================
    # INITIAL GRAPH SNAPSHOT
    # =====================================================

    graph_data = graph.get_graph()

    # =====================================================
    # TYPE INFERENCE ENGINE
    # =====================================================

    type_engine = TypeInferenceEngine(
        graph_data
    )

    inferred_types = (
        type_engine.infer_types()
    )

    logger.debug("Inferred types: %s", inferred_types)

    graph_data[
        "inferred_types"
    ] = inferred_types

    # =====================================================
    # ADD SYNTHETIC TYPE NODES
    # =====================================================

    for variable_name, variable_type in inferred_types.items():

        if not is_valid_semantic_token(
            variable_name
        ):
            continue

        if variable_name not in graph_data["nodes"]:

            graph.add_node(

                node_id=variable_name,

                node_type="inferred_variable",

                metadata={

                    "variable_name":
                    variable_name,

                    "inferred_type":
                    variable_type,

                    "synthetic":
                    True
                }
            )

    # =====================================================
    # REFRESH GRAPH SNAPSHOT
    # =====================================================

    graph_data = graph.get_graph()

    # =====================================================
    # BUILD SYMBOL TABLE
    # =====================================================

    symbol_table_engine = RepositorySymbolTable(
        graph_data
    )

    symbol_table = (
        symbol_table_engine
        .build_symbol_table()
    )

    graph_data[
        "symbol_table"
    ] = symbol_table

    # =====================================================
    # SYMBOL RESOLUTION ENGINE
    # =====================================================

    resolution_engine = SymbolResolutionEngine(
        graph_data
    )

    resolved_symbols = []

    for edge in graph_data.get(
        "edges",
        []
    ):

        if edge.get(
            "relationship"
        ) != "calls":

            continue

        resolution = (

            resolution_engine.resolve_symbol(

                edge.get("source"),

                edge.get("target")
            )
        )

        resolved_symbols.append(
            resolution
        )

    graph_data[
        "resolved_symbols"
    ] = resolved_symbols

    # =====================================================
    # METHOD COMPATIBILITY ENGINE
    # =====================================================

    graph_data = graph.get_graph()

    graph_data[
        "inferred_types"
    ] = inferred_types

    graph_data[
        "symbol_table"
    ] = symbol_table

    graph_data[
        "resolved_symbols"
    ] = resolved_symbols

    compatibility_engine = (
        MethodCompatibilityEngine(
            graph_data
        )
    )

    compatibility_findings = (
        compatibility_engine
        .detect_compatibility_issues()
    )

    logger.debug("Compatibility findings: %s", compatibility_findings)

    graph_data[
        "compatibility_findings"
    ] = compatibility_findings

    # =====================================================
    # NORMALIZE FINDINGS
    # =====================================================

    normalized_findings = []

    for finding in compatibility_findings:

        if (

            "invalid_method" in finding
            and
            "method" not in finding

        ):

            finding["method"] = (
                finding.get(
                    "invalid_method"
                )
            )

        normalized_findings.append(
            finding
        )

    # =====================================================
    # MERGE SYMBOLIC FINDINGS
    # =====================================================

    existing_findings = graph_data.get(
        "symbolic_findings",
        []
    )

    existing_findings.extend(
        normalized_findings
    )

    graph_data[
        "symbolic_findings"
    ] = existing_findings

    # =====================================================
    # FINAL GRAPH SNAPSHOT
    # =====================================================

    final_graph_data = graph.get_graph()

    final_graph_data[
        "inferred_types"
    ] = inferred_types

    final_graph_data[
        "symbol_table"
    ] = symbol_table

    final_graph_data[
        "resolved_symbols"
    ] = resolved_symbols

    final_graph_data[
        "compatibility_findings"
    ] = normalized_findings

    final_graph_data[
        "symbolic_findings"
    ] = existing_findings

    # =====================================================
    # ACTIVE GRAPH MEMORY
    # =====================================================

    repository_graph_memory[
        "active_graph"
    ] = final_graph_data

    return final_graph_data