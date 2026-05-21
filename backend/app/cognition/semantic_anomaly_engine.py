# ==========================================
# SEMANTIC ANOMALY ENGINE
# ==========================================

class SemanticAnomalyEngine:

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

    # ======================================
    # DETECT GRAPH ANOMALIES
    # ======================================

    def detect_anomalies(self):

        anomalies = []

        # ==================================
        # CONNECTED NODE TRACKING
        # ==================================

        connected_nodes = set()

        for edge in self.edges:

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            if source:

                connected_nodes.add(
                    source
                )

            if target:

                connected_nodes.add(
                    target
                )

        # ==================================
        # ORPHAN NODE DETECTION
        # ==================================

        for node_id, node_data in self.nodes.items():

            node_type = node_data.get(
                "type"
            )

            metadata = node_data.get(
                "metadata",
                {}
            )

            # ==============================
            # IGNORE SYNTHETIC NODES
            # ==============================

            if metadata.get(
                "synthetic"
            ):

                continue

            # ==============================
            # IGNORE INFRASTRUCTURE NODES
            # ==============================

            if node_type in [

                "raw_source",
                "repository_root",
                "inferred_variable"

            ]:

                continue

            # ==============================
            # IGNORE CALL SIGNATURE NODES
            # ==============================

            if node_type == "calls":

                continue

            # ==============================
            # ORPHAN DETECTION
            # ==============================

            if node_id not in connected_nodes:

                anomalies.append({

                    "issue_type":
                    "orphan_semantic_node",

                    "node":
                    node_id,

                    "node_type":
                    node_type,

                    "reason":
                    "Semantic node disconnected from graph"
                })

        # ==================================
        # DANGLING EDGE DETECTION
        # ==================================

        existing_nodes = set(
            self.nodes.keys()
        )

        for edge in self.edges:

            relationship = edge.get(
                "relationship"
            )

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            # ==============================
            # IGNORE CALL RELATIONSHIPS
            # ==============================

            if relationship == "calls":

                continue

            # ==============================
            # MISSING SOURCE
            # ==============================

            if (

                source and
                source not in existing_nodes

            ):

                anomalies.append({

                    "issue_type":
                    "dangling_source_reference",

                    "source":
                    source,

                    "edge":
                    edge,

                    "reason":
                    "Edge source missing from semantic graph"
                })

            # ==============================
            # MISSING TARGET
            # ==============================

            if (

                target and
                target not in existing_nodes

            ):

                anomalies.append({

                    "issue_type":
                    "dangling_target_reference",

                    "target":
                    target,

                    "edge":
                    edge,

                    "reason":
                    "Edge target missing from semantic graph"
                })

        # ==================================
        # RETURN DETECTED ANOMALIES
        # ==================================

        return anomalies