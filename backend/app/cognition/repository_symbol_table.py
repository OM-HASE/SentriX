# ==========================================
# REPOSITORY SYMBOL TABLE
# ==========================================

class RepositorySymbolTable:

    def __init__(

        self,

        graph
    ):

        self.graph = graph

        self.nodes = graph.get(
            "nodes",
            {}
        )

    # ======================================
    # BUILD SYMBOL TABLE
    # ======================================

    def build_symbol_table(
        self
    ):

        symbol_table = {

            "classes": {},
            "functions": {},
            "methods": {},
            "imports": {}
        }

        # ==================================
        # NODE ANALYSIS
        # ==================================

        for node_id, node_data in (

            self.nodes.items()
        ):

            node_type = node_data.get(
                "type"
            )

            metadata = node_data.get(
                "metadata",
                {}
            )

            entity_name = metadata.get(
                "entity_name"
            )

            file_path = metadata.get(
                "file_path"
            )

            parent = metadata.get(
                "parent"
            )

            # ==============================
            # CLASS DEFINITIONS
            # ==============================

            if node_type == (
                "class_definition"
            ):

                symbol_table[
                    "classes"
                ][entity_name] = {

                    "file_path":
                    file_path,

                    "methods":
                    [],

                    "metadata":
                    metadata
                }

            # ==============================
            # FUNCTION DEFINITIONS
            # ==============================

            elif node_type == (
                "function_definition"
            ):

                # ==========================
                # CLASS METHOD
                # ==========================

                if parent:

                    qualified_name = (
                        f"{parent}.{entity_name}"
                    )

                    symbol_table[
                        "methods"
                    ][qualified_name] = {

                        "class":
                        parent,

                        "method":
                        entity_name,

                        "file_path":
                        file_path,

                        "metadata":
                        metadata
                    }

                    # ======================
                    # REGISTER TO CLASS
                    # ======================

                    if parent in (
                        symbol_table[
                            "classes"
                        ]
                    ):

                        symbol_table[
                            "classes"
                        ][parent][
                            "methods"
                        ].append(
                            entity_name
                        )

                # ==========================
                # GLOBAL FUNCTION
                # ==========================

                else:

                    symbol_table[
                        "functions"
                    ][entity_name] = {

                        "file_path":
                        file_path,

                        "metadata":
                        metadata
                    }

            # ==============================
            # IMPORTS
            # ==============================

            elif node_type == (
                "imports"
            ):

                module_name = metadata.get(
                    "module"
                )

                if module_name:

                    symbol_table[
                        "imports"
                    ][module_name] = {

                        "file_path":
                        file_path,

                        "metadata":
                        metadata
                    }

        return symbol_table