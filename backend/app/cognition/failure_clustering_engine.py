# ==========================================
# FAILURE CLUSTERING ENGINE
# ==========================================

class FailureClusteringEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        symbolic_findings,

        propagation_analysis
    ):

        self.symbolic_findings = (
            symbolic_findings or []
        )

        self.propagation_analysis = (
            propagation_analysis or {}
        )

    # ======================================
    # CLUSTER FAILURES
    # ======================================

    def cluster_failures(
        self
    ):

        clustering = {

            "failure_clusters": [],

            "root_failure_groups": [],

            "cluster_count": 0
        }

        grouped = {}

        # ==================================
        # SYMBOLIC FINDING GROUPING
        # ==================================

        for finding in self.symbolic_findings:

            issue_type = finding.get(
                "issue_type",
                "unknown"
            )

            if issue_type not in grouped:

                grouped[
                    issue_type
                ] = []

            grouped[
                issue_type
            ].append(
                finding
            )

        # ==================================
        # BUILD CLUSTERS
        # ==================================

        for issue_type, findings in (

            grouped.items()
        ):

            cluster = {

                "cluster_type":
                issue_type,

                "cluster_size":
                len(findings),

                "findings":
                findings,

                "propagation_related":
                False
            }

            propagation_paths = (

                self.propagation_analysis.get(
                    "propagation_paths",
                    []
                )
            )

            if propagation_paths:

                cluster[
                    "propagation_related"
                ] = True

            clustering[
                "failure_clusters"
            ].append(
                cluster
            )

        # ==================================
        # ROOT FAILURE GROUPS
        # ==================================

        for cluster in (

            clustering[
                "failure_clusters"
            ]
        ):

            root_group = {

                "root_issue":
                cluster.get(
                    "cluster_type"
                ),

                "affected_components":
                cluster.get(
                    "cluster_size"
                ),

                "systemic_impact":
                cluster.get(
                    "propagation_related"
                )
            }

            clustering[
                "root_failure_groups"
            ].append(
                root_group
            )

        # ==================================
        # CLUSTER COUNT
        # ==================================

        clustering[
            "cluster_count"
        ] = len(

            clustering[
                "failure_clusters"
            ]
        )

        return clustering