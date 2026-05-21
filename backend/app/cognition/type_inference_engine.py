# ==========================================
# TYPE INFERENCE ENGINE
# ==========================================

class TypeInferenceEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

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

    # ======================================
    # MAIN TYPE INFERENCE
    # ======================================

    def infer_types(
        self
    ):

        inferred_types = {}

        # ==================================
        # NODE ANALYSIS
        # ==================================

        for node_id, node_data in (

            self.nodes.items()
        ):

            metadata = node_data.get(
                "metadata",
                {}
            )

            # ==============================
            # ENTITY CONTENT
            # ==============================

            content = metadata.get(
                "content",
                ""
            )

            if content:

                extracted = (

                    self.extract_variable_types(
                        content
                    )
                )

                inferred_types.update(
                    extracted
                )

            # ==============================
            # RAW SOURCE
            # ==============================

            source_code = metadata.get(
                "source_code",
                ""
            )

            if source_code:

                extracted = (

                    self.extract_variable_types(
                        source_code
                    )
                )

                inferred_types.update(
                    extracted
                )

        # ==================================
        # GRAPH PROPAGATION
        # ==================================

        propagated = (

            self.propagate_types(
                inferred_types
            )
        )

        inferred_types.update(
            propagated
        )

        # ==================================
        # SEMANTIC NORMALIZATION
        # ==================================

        normalized = (

            self.normalize_types(
                inferred_types
            )
        )

        return normalized

    # ======================================
    # VARIABLE TYPE EXTRACTION
    # ======================================

    def extract_variable_types(

        self,

        source
    ):

        inferred = {}

        if not source:

            return inferred

        lines = source.splitlines()

        for line in lines:

            stripped = line.strip()

            if not stripped:

                continue

            # ==================================
            # ASSIGNMENT STRUCTURE
            # ==================================

            if "=" not in stripped:

                continue

            parts = stripped.split("=")

            if len(parts) < 2:

                continue

            left_side = (
                parts[0].strip()
            )

            right_side = (
                parts[1].strip()
            )

            # ==================================
            # LEFT TOKENS
            # ==================================

            left_tokens = left_side.split()

            # ==================================
            # SEMANTIC DECLARATION INFERENCE
            # ==================================

            if len(left_tokens) >= 2:

                probable_type = (
                    left_tokens[-2]
                )

                variable_name = (
                    left_tokens[-1]
                )

                probable_type = (

                    probable_type
                    .replace(";", "")
                    .replace("*", "")
                    .replace("&", "")
                    .replace("[]", "")
                    .strip()
                )

                variable_name = (

                    variable_name
                    .replace(";", "")
                    .strip()
                )

                # ==============================
                # GENERIC NORMALIZATION
                # ==============================

                probable_type = (

                    self.clean_type_signature(
                        probable_type
                    )
                )

                # ==============================
                # VALID SEMANTIC PAIR
                # ==============================

                if (

                    probable_type and
                    variable_name and
                    probable_type != variable_name

                ):

                    inferred[
                        variable_name
                    ] = probable_type

            # ==================================
            # CONSTRUCTOR-BASED INFERENCE
            # ==================================

            if "(" in right_side:

                constructor_name = (

                    right_side
                    .split("(")[0]
                    .strip()
                )

                constructor_name = (

                    self.clean_type_signature(
                        constructor_name
                    )
                )

                variable_name = (
                    left_side.split()[-1]
                    .strip()
                )

                if (

                    constructor_name and
                    variable_name

                ):

                    inferred[
                        variable_name
                    ] = constructor_name

        return inferred

    # ======================================
    # CLEAN TYPE SIGNATURE
    # ======================================

    def clean_type_signature(

        self,

        signature
    ):

        if not signature:

            return ""

        cleaned = signature

        # ==================================
        # GENERIC REMOVAL
        # ==================================

        if "<" in cleaned:

            cleaned = (
                cleaned.split("<")[0]
            )

        # ==================================
        # NAMESPACE REDUCTION
        # ==================================

        if "::" in cleaned:

            cleaned = (
                cleaned.split("::")[-1]
            )

        if "." in cleaned:

            cleaned = (
                cleaned.split(".")[-1]
            )

        cleaned = (

            cleaned
            .replace("*", "")
            .replace("&", "")
            .replace(";", "")
            .strip()
        )

        return cleaned

    # ======================================
    # TYPE PROPAGATION
    # ======================================

    def propagate_types(

        self,

        inferred_types
    ):

        propagated = {}

        for edge in self.edges:

            relationship = edge.get(
                "relationship"
            )

            if relationship != "calls":

                continue

            source_object = edge.get(
                "source"
            )

            if not source_object:

                continue

            inferred_type = inferred_types.get(
                source_object
            )

            if inferred_type:

                propagated[
                    source_object
                ] = inferred_type

        return propagated

    # ======================================
    # TYPE NORMALIZATION
    # ======================================

    def normalize_types(

        self,

        inferred_types
    ):

        normalized = {}

        for variable, inferred_type in (

            inferred_types.items()
        ):

            cleaned = (

                self.clean_type_signature(
                    inferred_type
                )
            )

            normalized[
                variable
            ] = cleaned

        return normalized