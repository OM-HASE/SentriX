# ==========================================
# FAILURE PROPAGATION ENGINE
# ==========================================

class FailurePropagationEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        graph,

        findings
    ):

        self.graph = graph

        self.findings = (
            findings or []
        )

        self.edges = graph.get(
            "edges",
            []
        )

        # ==================================
        # EXECUTION FLOW
        # ==================================

        self.execution_flow = [

            edge for edge in self.edges

            if edge.get(
                "relationship"
            ) == "calls"
        ]

        # ==================================
        # SYMBOLIC FINDINGS
        # ==================================

        self.symbolic_findings = [

            finding for finding in self.findings

            if finding.get(
                "issue_type"
            ) in [

                "symbolic_invocation",
                "method_compatibility_failure",
                "unresolved_symbol",
                "unresolved_method",
                "none_type_method_call",
                "semantic_failure"
            ]
        ]

    # ======================================
    # ANALYZE PROPAGATION
    # ======================================

    def analyze_propagation(

        self
    ):

        propagation_paths = []

        affected_nodes = set()

        symbolic_findings = (
            self.symbolic_findings
        )

        execution_flow = (
            self.execution_flow
        )

        # ==================================
        # BUILD EXECUTION MAP
        # ==================================

        adjacency_map = {}

        for edge in execution_flow:

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            if not source or not target:

                continue

            if source not in adjacency_map:

                adjacency_map[
                    source
                ] = []

            adjacency_map[
                source
            ].append(
                target
            )

        # ==================================
        # DFS PROPAGATION
        # ==================================

        def propagate(

            node,

            visited=None,

            depth=0
        ):

            if visited is None:

                visited = set()

            if node in visited:

                return

            if depth > 10:

                return

            visited.add(
                node
            )

            affected_nodes.add(
                node
            )

            next_nodes = adjacency_map.get(

                node,

                []
            )

            for next_node in next_nodes:

                propagation_paths.append({

                    "source":
                    node,

                    "target":
                    next_node,

                    "relationship":
                    "propagates_to",

                    "depth":
                    depth + 1
                })

                propagate(

                    next_node,

                    visited,

                    depth + 1
                )

        # ==================================
        # START PROPAGATION
        # ==================================

        for finding in symbolic_findings:

            symbol = finding.get(
                "symbol"
            )

            object_name = finding.get(
                "object"
            )

            method_name = finding.get(
                "method"
            )

            if symbol:

                propagate(
                    symbol
                )

            if object_name:

                propagate(
                    object_name
                )

            if method_name:

                propagate(
                    method_name
                )

        # ==================================
        # RESULT
        # ==================================

        return {

            "propagation_paths":
            propagation_paths,

            "affected_nodes":
            list(affected_nodes),

            "blast_radius":
            len(affected_nodes),

            "execution_instability":
            len(affected_nodes) > 3,

            "failure_propagation_depth":
            len(propagation_paths)
        }

    # ======================================
    # SEMANTIC MATCH
    # ======================================

    def semantic_match(

        self,

        failure_node,

        source,

        target
    ):

        if not failure_node:

            return False

        candidates = [

            str(source or ""),

            str(target or "")
        ]

        for candidate in candidates:

            # ==============================
            # DIRECT MATCH
            # ==============================

            if candidate == failure_node:

                return True

            # ==============================
            # SEMANTIC CONTAINMENT
            # ==============================

            if failure_node in candidate:

                return True

            # ==============================
            # TOKEN OVERLAP
            # ==============================

            failure_tokens = set(
                failure_node.split(".")
            )

            candidate_tokens = set(
                candidate.split(".")
            )

            overlap = (

                failure_tokens
                &
                candidate_tokens
            )

            if overlap:

                return True

        return False