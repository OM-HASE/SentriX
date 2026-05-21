# ==========================================
# SEMANTIC PRIORITIZATION ENGINE
# ==========================================

class SemanticPrioritizationEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        findings
    ):

        self.findings = (
            findings or []
        )

    # ======================================
    # PRIORITIZE FINDINGS
    # ======================================

    def prioritize_findings(
        self
    ):

        prioritized = []

        for finding in self.findings:

            issue_type = finding.get(
                "issue_type",
                ""
            )

            priority_score = (
                self.calculate_priority(
                    finding
                )
            )

            finding[
                "priority_score"
            ] = priority_score

            finding[
                "priority_level"
            ] = (
                self.priority_label(
                    priority_score
                )
            )

            prioritized.append(
                finding
            )

        # ==================================
        # SORT DESCENDING
        # ==================================

        prioritized.sort(

            key=lambda x:
            x.get(
                "priority_score",
                0
            ),

            reverse=True
        )

        return prioritized

    # ======================================
    # PRIORITY CALCULATION
    # ======================================

    def calculate_priority(

        self,

        finding
    ):

        issue_type = finding.get(
            "issue_type",
            ""
        )

        score = 0

        # ==================================
        # EXECUTION BREAKING FAILURES
        # ==================================

        if (

            "method" in issue_type

            or

            "symbol" in issue_type

            or

            "compatibility" in issue_type

        ):

            score += 100

        # ==================================
        # PROPAGATION FAILURES
        # ==================================

        if (

            "propagation" in issue_type

            or

            "runtime" in issue_type

        ):

            score += 70

        # ==================================
        # GRAPH INSTABILITY
        # ==================================

        if (

            "dangling" in issue_type

        ):

            score += 40

        # ==================================
        # LOW-IMPACT GRAPH NOISE
        # ==================================

        if (

            "orphan" in issue_type

        ):

            score += 10

        # ==================================
        # EXECUTION CONTEXT BOOST
        # ==================================

        if finding.get(
            "method"
        ):

            score += 20

        if finding.get(
            "object"
        ):

            score += 20

        return score

    # ======================================
    # PRIORITY LABEL
    # ======================================

    def priority_label(

        self,

        score
    ):

        if score >= 100:

            return "critical"

        if score >= 70:

            return "high"

        if score >= 40:

            return "medium"

        return "low"