# ==========================================
# SYMBOL RESOLUTION ENGINE
# ==========================================

class SymbolResolutionEngine:

    def __init__(

        self,

        graph
    ):

        self.graph = graph

        self.nodes = graph.get(
            "nodes",
            {}
        )

        self.edges = graph.get(
            "edges",
            []
        )

        self.inferred_types = graph.get(
            "inferred_types",
            {}
        )

        self.symbol_table = graph.get(
            "symbol_table",
            {}
        )

    # ======================================
    # MAIN RESOLUTION
    # ======================================

    def resolve_symbol(

        self,

        object_name,

        method_name
    ):

        # ==================================
        # GLOBAL SYMBOLS
        # ==================================

        if object_name == "global":

            return self.resolve_global_symbol(
                method_name
            )

        # ==================================
        # TYPE-AWARE RESOLUTION
        # ==================================

        type_resolution = (

            self.resolve_type_method(

                object_name,

                method_name
            )
        )

        if type_resolution:

            return type_resolution

        # ==================================
        # SEMANTIC EDGE MATCHING
        # ==================================

        matching_edges = [

            edge

            for edge in self.edges

            if (

                edge.get("source") == object_name

                and

                edge.get("target") == method_name

                and

                edge.get("relationship") == "calls"

            )
        ]

        # ==================================
        # SEMANTIC CONFIDENCE
        # ==================================

        if matching_edges:

            confidence = len(
                matching_edges
            )

            return {

                "resolved": True,

                "resolution_type":
                "semantic_graph_match",

                "object":
                object_name,

                "method":
                method_name,

                "confidence":
                confidence
            }

        # ==================================
        # IMPORT CONTEXT INFERENCE
        # ==================================

        if self.has_import_context():

            return {

                "resolved": False,

                "resolution_type":
                "unverified_dependency_method",

                "object":
                object_name,

                "method":
                method_name
            }

        # ==================================
        # UNRESOLVED
        # ==================================

        return {

            "resolved": False,

            "resolution_type":
            "unresolved_symbol",

            "object":
            object_name,

            "method":
            method_name
        }

    # ======================================
    # TYPE-AWARE METHOD RESOLUTION
    # ======================================

    def resolve_type_method(

        self,

        object_name,

        method_name
    ):

        object_type = (

            self.inferred_types.get(
                object_name
            )
        )

        if not object_type:

            return None

        methods = self.symbol_table.get(
            "methods",
            {}
        )

        qualified_name = (
            f"{object_type}.{method_name}"
        )

        # ==================================
        # CLASS METHOD MATCH
        # ==================================

        if qualified_name in methods:

            return {

                "resolved": True,

                "resolution_type":
                "type_method_match",

                "object":
                object_name,

                "object_type":
                object_type,

                "method":
                method_name,

                "resolved_to":
                qualified_name
            }

        return None

    # ======================================
    # GLOBAL SYMBOL RESOLUTION
    # ======================================

    def resolve_global_symbol(

        self,

        method_name
    ):

        for node_id, node_data in self.nodes.items():

            metadata = node_data.get(
                "metadata",
                {}
            )

            entity_name = metadata.get(
                "entity_name"
            )

            if entity_name == method_name:

                return {

                    "resolved": True,

                    "resolution_type":
                    "repository_entity_match",

                    "method":
                    method_name
                }

        return {

            "resolved": False,

            "resolution_type":
            "unresolved_global_symbol",

            "method":
            method_name
        }

    # ======================================
    # IMPORT CONTEXT
    # ======================================

    def has_import_context(
        self
    ):

        for edge in self.edges:

            if edge.get(
                "relationship"
            ) == "imports":

                return True

        return False