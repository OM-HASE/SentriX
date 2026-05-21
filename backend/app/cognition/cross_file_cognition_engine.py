# ==========================================
# CROSS FILE COGNITION ENGINE
# ==========================================

class CrossFileCognitionEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        graph,

        symbolic_findings
    ):

        self.graph = graph

        self.symbolic_findings = (
            symbolic_findings or []
        )

        self.nodes = graph.get(
            "nodes",
            {}
        )

        self.edges = graph.get(
            "edges",
            []
        )

    # ======================================
    # ANALYZE CROSS FILE IMPACT
    # ======================================

    def analyze_cross_file_impact(
        self
    ):

        analysis = {

            "affected_files": [],

            "cross_file_dependencies": [],

            "repository_instability": False,

            "impact_radius": 0,

            "dependency_chains": []
        }

        affected_files = set()

        dependency_chains = []

        # ==================================
        # FIND FAILURE OBJECTS
        # ==================================

        failure_objects = set()

        for finding in self.symbolic_findings:

            object_name = finding.get(
                "object"
            )

            if object_name:

                failure_objects.add(
                    object_name
                )

        # ==================================
        # TRACE GRAPH IMPACT
        # ==================================

        for node_id, node_data in (

            self.nodes.items()
        ):

            metadata = node_data.get(
                "metadata",
                {}
            )

            file_path = metadata.get(
                "file_path"
            )

            # ==============================
            # FAILURE NODE MATCH
            # ==============================

            for failure_object in failure_objects:

                if failure_object in node_id:

                    if file_path:

                        affected_files.add(
                            file_path
                        )

        # ==================================
        # IMPORT DEPENDENCY TRACING
        # ==================================

        for edge in self.edges:

            relationship = edge.get(
                "relationship"
            )

            if relationship != "imports":

                continue

            source = edge.get(
                "source"
            )

            target = edge.get(
                "target"
            )

            dependency_chains.append({

                "source":
                source,

                "target":
                target,

                "relationship":
                relationship
            })

        # ==================================
        # IMPACT RADIUS
        # ==================================

        analysis[
            "impact_radius"
        ] = len(
            affected_files
        )

        # ==================================
        # REPOSITORY INSTABILITY
        # ==================================

        if len(affected_files) > 1:

            analysis[
                "repository_instability"
            ] = True

        # ==================================
        # FINAL RESULTS
        # ==================================

        analysis[
            "affected_files"
        ] = list(
            affected_files
        )

        analysis[
            "dependency_chains"
        ] = dependency_chains

        analysis[
            "cross_file_dependencies"
        ] = dependency_chains

        return analysis