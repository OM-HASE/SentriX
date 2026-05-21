# ==========================================
# METHOD COMPATIBILITY ENGINE
# ==========================================

from difflib import get_close_matches


class MethodCompatibilityEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(self, graph):

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

        self.resolved_symbols = graph.get(
            "resolved_symbols",
            []
        )

    # ======================================
    # DETECT COMPATIBILITY ISSUES
    # ======================================

    def detect_compatibility_issues(self):

        findings = []

        # ==================================
        # BUILD REGISTRIES
        # ==================================

        method_registry = (
            self.build_method_registry()
        )

        standard_registry = (
            self.build_standard_registry()
        )

        # ==================================
        # ANALYZE CALL RELATIONSHIPS
        # ==================================

        for edge in self.edges:

            if edge.get(
                "relationship"
            ) != "calls":

                continue

            object_name = edge.get(
                "source"
            )

            raw_target = edge.get(
                "target"
            )
            method_name = (raw_target
                           .split(".")[-1]
                           .strip())

            # ==============================
            # OBJECT TYPE
            # ==============================

            object_type = self.inferred_types.get(
                object_name
            )

            if not object_type:
                continue

            # ==============================
            # NORMALIZE TYPE
            # ==============================

            normalized_type = (
                object_type
                .split(".")[-1]
                .split("<")[0]
                .replace("[]", "")
                .strip()
            )

            # ==============================
            # FETCH VALID METHODS
            # ==============================

            repository_methods = (
                method_registry.get(
                    normalized_type,
                    set()
                )
            )

            standard_methods = (
                standard_registry.get(
                    normalized_type,
                    set()
                )
            )

            valid_methods = set()

            valid_methods.update(
                repository_methods
            )

            valid_methods.update(
                standard_methods
            )

            # ==============================
            # DEBUG LOGGING
            # ==============================

            print("\n========== DEBUG ==========\n")
            print("OBJECT:", object_name)
            print("TYPE:", normalized_type)
            print("VALID METHODS:", valid_methods)
            print("METHOD:", method_name)

            # ==============================
            # UNKNOWN TYPE
            # ==============================

            if not valid_methods:
                continue

            # ==============================
            # VALID METHOD
            # ==============================

            if method_name in valid_methods:
                continue

            # ==============================
            # CLOSEST MATCH
            # ==============================

            closest_method = (
                self.find_closest_method(
                    method_name,
                    valid_methods
                )
            )

            # ==============================
            # COMPATIBILITY FAILURE
            # ==============================

            findings.append({

                "issue_type":
                "method_compatibility_failure",

                "object":
                object_name,

                "object_type":
                normalized_type,

                "invalid_method":
                method_name,

                "closest_match":
                closest_method,

                "available_methods":
                sorted(
                    list(valid_methods)
                )[:15],

                "reason":
                "Method incompatible with inferred object type"
            })

        return findings

    # ======================================
    # BUILD REPOSITORY METHOD REGISTRY
    # ======================================

    def build_method_registry(self):

        registry = {}

        methods = self.symbol_table.get(
            "methods",
            {}
        )

        for qualified_name, metadata in methods.items():

            class_name = metadata.get(
                "class"
            )

            method_name = metadata.get(
                "method"
            )

            if (
                not class_name or
                not method_name
            ):
                continue

            normalized_class = (
                class_name
                .split(".")[-1]
                .strip()
            )

            if normalized_class not in registry:

                registry[
                    normalized_class
                ] = set()

            registry[
                normalized_class
            ].add(
                method_name
            )

        return registry

    # ======================================
    # STANDARD LIBRARY METHOD REGISTRY
    # ======================================

    def build_standard_registry(self):

        return {

            # ==============================
            # JAVA STANDARD TYPES
            # ==============================

            "ArrayList": {

                "add",
                "remove",
                "clear",
                "get",
                "set",
                "size",
                "contains",
                "isEmpty"
            },

            "HashMap": {

                "put",
                "get",
                "remove",
                "containsKey",
                "containsValue",
                "clear",
                "size"
            },

            "String": {

                "length",
                "substring",
                "charAt",
                "contains",
                "replace",
                "trim",
                "toLowerCase",
                "toUpperCase"
            },

            # ==============================
            # PYTHON STANDARD TYPES
            # ==============================

            "list": {

                "append",
                "remove",
                "clear",
                "pop",
                "extend",
                "insert",
                "index"
            },

            "dict": {

                "get",
                "keys",
                "values",
                "items",
                "update",
                "pop"
            },

            "PrintStream":{
                "println",
                "print",
                "printf"
            }
        }

    # ======================================
    # FIND CLOSEST METHOD MATCH
    # ======================================

    def find_closest_method(

        self,
        invalid_method,
        valid_methods
    ):

        closest = get_close_matches(

            invalid_method,

            list(valid_methods),

            n=1,

            cutoff=0.5
        )

        if closest:
            return closest[0]

        return None