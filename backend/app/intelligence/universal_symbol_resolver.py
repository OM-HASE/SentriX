from collections import defaultdict


# ==========================================
# UNIVERSAL SYMBOL RESOLVER
# ==========================================

class UniversalSymbolResolver:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        semantic_relationships,

        code_entities,

        language
    ):

        self.semantic_relationships = (
            semantic_relationships or []
        )

        self.code_entities = (
            code_entities or []
        )

        self.language = (
            language or "unknown"
        )

        self.symbol_table = {}

        self.class_registry = {}

        self.standard_library_registry = (
            self.build_standard_library_registry()
        )

    # ======================================
    # STANDARD LIBRARY REGISTRY
    # ======================================

    def build_standard_library_registry(
        self
    ):

        return {

            "cpp": {

                "vector": {

                    "push_back",
                    "pop_back",
                    "size",
                    "begin",
                    "end",
                    "clear",
                    "resize",
                    "empty",
                    "insert",
                    "erase"
                },

                "map": {

                    "insert",
                    "erase",
                    "find",
                    "clear",
                    "size",
                    "empty"
                }
            },

            "java": {

                "ArrayList": {

                    "add",
                    "remove",
                    "clear",
                    "size",
                    "contains",
                    "get",
                    "set",
                    "isEmpty"
                },

                "HashMap": {

                    "put",
                    "get",
                    "remove",
                    "containsKey",
                    "clear",
                    "size"
                }
            },

            "javascript": {

                "Array": {

                    "push",
                    "pop",
                    "map",
                    "filter",
                    "forEach",
                    "reduce",
                    "slice",
                    "splice",
                    "length"
                }
            },

            "go": {

                "slice": {

                    "append",
                    "len",
                    "cap"
                }
            }
        }

    # ======================================
    # BUILD SYMBOL TABLE
    # ======================================

    def build_symbol_table(
        self
    ):

        for entity in self.code_entities:

            entity_name = entity.get(
                "entity_name"
            )

            entity_type = entity.get(
                "entity_type"
            )

            content = entity.get(
                "content",
                ""
            )

            if not entity_name:

                continue

            # ==============================
            # CLASS REGISTRY
            # ==============================

            if entity_type in [

                "class_definition",
                "class_declaration",
                "class"
            ]:

                self.class_registry[
                    entity_name
                ] = {

                    "methods":
                    self.extract_methods_from_class(
                        content
                    )
                }

            # ==============================
            # TYPE INFERENCE
            # ==============================

            inferred_types = (
                self.infer_variable_types(
                    content
                )
            )

            for variable, var_type in (

                inferred_types.items()
            ):

                self.symbol_table[
                    variable
                ] = var_type

    # ======================================
    # EXTRACT METHODS
    # ======================================

    def extract_methods_from_class(

        self,

        content
    ):

        methods = set()

        lines = content.splitlines()

        for line in lines:

            stripped = line.strip()

            if "(" not in stripped:

                continue

            if ")" not in stripped:

                continue

            if "." in stripped:

                continue

            tokens = stripped.split("(")[0]

            method_name = (
                tokens.split()[-1]
                .strip()
            )

            if method_name:

                methods.add(
                    method_name
                )

        return methods

    # ======================================
    # TYPE INFERENCE
    # ======================================

    def infer_variable_types(

        self,

        content
    ):

        inferred = {}

        lines = content.splitlines()

        for line in lines:

            stripped = line.strip()

            # ==============================
            # C++ VECTOR
            # ==============================

            if "vector<" in stripped:

                parts = stripped.split()

                if len(parts) >= 2:

                    variable = (
                        parts[-1]
                        .replace(";", "")
                    )

                    inferred[
                        variable
                    ] = "vector"

            # ==============================
            # C++ MAP
            # ==============================

            elif "map<" in stripped:

                parts = stripped.split()

                if len(parts) >= 2:

                    variable = (
                        parts[-1]
                        .replace(";", "")
                    )

                    inferred[
                        variable
                    ] = "map"

            # ==============================
            # JAVA ARRAYLIST
            # ==============================

            elif "ArrayList<" in stripped:

                parts = stripped.split()

                if len(parts) >= 2:

                    variable = (
                        parts[-1]
                        .replace(";", "")
                    )

                    inferred[
                        variable
                    ] = "ArrayList"

            # ==============================
            # JAVA HASHMAP
            # ==============================

            elif "HashMap<" in stripped:

                parts = stripped.split()

                if len(parts) >= 2:

                    variable = (
                        parts[-1]
                        .replace(";", "")
                    )

                    inferred[
                        variable
                    ] = "HashMap"

        return inferred

    # ======================================
    # RESOLVE METHOD
    # ======================================

    def resolve_method(

        self,

        object_name,

        method_name
    ):

        object_type = self.symbol_table.get(
            object_name
        )

        if not object_type:

            return {

                "resolved": False,

                "reason":
                "unknown_object_type"
            }

        # ==================================
        # STANDARD LIBRARY
        # ==================================

        language_registry = (

            self.standard_library_registry.get(
                self.language,
                {}
            )
        )

        available_methods = (

            language_registry.get(
                object_type,
                set()
            )
        )

        if method_name in available_methods:

            return {

                "resolved": True,

                "type": object_type,

                "source":
                "standard_library"
            }

        # ==================================
        # CLASS REGISTRY
        # ==================================

        class_info = self.class_registry.get(
            object_type
        )

        if class_info:

            methods = class_info.get(
                "methods",
                set()
            )

            if method_name in methods:

                return {

                    "resolved": True,

                    "type": object_type,

                    "source":
                    "class_registry"
                }

        # ==================================
        # FAILURE
        # ==================================

        return {

            "resolved": False,

            "type": object_type,

            "reason":
            "missing_method"
        }

    # ======================================
    # ANALYZE SYMBOLIC FAILURES
    # ======================================

    def analyze_symbolic_failures(
        self
    ):

        self.build_symbol_table()

        findings = []

        visited = set()

        for relationship in (

            self.semantic_relationships
        ):

            if (

                relationship.get(
                    "relationship_type"
                ) != "calls"

            ):

                continue

            object_name = relationship.get(
                "object"
            )

            method_name = relationship.get(
                "method"
            )

            if not object_name:

                continue

            if not method_name:

                continue

            signature = (
                f"{object_name}.{method_name}"
            )

            if signature in visited:

                continue

            visited.add(signature)

            resolution = self.resolve_method(

                object_name,

                method_name
            )

            # ==============================
            # ONLY UNRESOLVED FAILURES
            # ==============================

            if not resolution.get(
                "resolved"
            ):

                findings.append({

                    "issue_type":
                    "unresolved_method_invocation",

                    "object":
                    object_name,

                    "method":
                    method_name,

                    "symbol":
                    signature,

                    "inferred_type":
                    resolution.get(
                        "type",
                        "unknown"
                    ),

                    "reason":
                    resolution.get(
                        "reason"
                    ),

                    "severity":
                    "high"
                })

        return findings