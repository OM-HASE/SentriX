# ==========================================
# FAILURE GRAPH ENGINE
# ==========================================

class FailureGraphEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        findings,

        execution_cognition,

        propagation
    ):

        self.findings = (
            findings or []
        )

        self.execution_cognition = (
            execution_cognition or {}
        )

        self.propagation = (
            propagation or {}
        )

    # ======================================
    # BUILD FAILURE GRAPH
    # ======================================

    def build_failure_graph(
        self
    ):

        graph = {

            "nodes": [],

            "edges": []
        }

        node_registry = set()

        # ==================================
        # FAILURE FINDINGS
        # ==================================

        for finding in self.findings:

            object_name = finding.get(
                "object"
            )

            method_name = finding.get(
                "method"
            )

            node_name = finding.get(
                "node"
            )

            # ==============================
            # OBJECT NODE
            # ==============================

            if object_name:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=object_name,

                    node_type="failure_object"
                )

            # ==============================
            # METHOD NODE
            # ==============================

            if method_name:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=method_name,

                    node_type="failure_method"
                )

            # ==============================
            # GENERIC FAILURE NODE
            # ==============================

            if node_name:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=node_name,

                    node_type="failure_node"
                )

            # ==============================
            # OBJECT -> METHOD EDGE
            # ==============================

            if (

                object_name and
                method_name
            ):

                graph[
                    "edges"
                ].append({

                    "source":
                    object_name,

                    "target":
                    method_name,

                    "relationship":
                    "failure_origin"
                })

        # ==================================
        # EXECUTION FLOW
        # ==================================

        execution_flow = (

            self.execution_cognition.get(
                "execution_flow",
                []
            )
        )

        for edge in execution_flow:

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            relationship = edge.get(
                "relationship"
            )

            if source:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=source,

                    node_type="execution_node"
                )

            if target:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=target,

                    node_type="execution_node"
                )

            graph[
                "edges"
            ].append({

                "source":
                source,

                "target":
                target,

                "relationship":
                relationship
            })

        # ==================================
        # PROPAGATION PATHS
        # ==================================

        propagation_paths = (

            self.propagation.get(
                "propagation_paths",
                []
            )
        )

        for path in propagation_paths:

            source = path.get(
                "source"
            )

            target = path.get(
                "target"
            )

            relationship = path.get(
                "relationship"
            )

            if source:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=source,

                    node_type="propagation_node"
                )

            if target:

                self.add_node(

                    graph,
                    node_registry,

                    node_id=target,

                    node_type="propagation_node"
                )

            graph[
                "edges"
            ].append({

                "source":
                source,

                "target":
                target,

                "relationship":
                relationship
            })

        return graph

    # ======================================
    # ADD NODE
    # ======================================

    def add_node(

        self,

        graph,

        registry,

        node_id,

        node_type
    ):

        if not node_id:

            return

        if node_id in registry:

            return

        registry.add(
            node_id
        )

        graph[
            "nodes"
        ].append({

            "id":
            node_id,

            "type":
            node_type
        })