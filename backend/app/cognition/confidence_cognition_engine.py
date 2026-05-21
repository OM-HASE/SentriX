from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ==========================================
# CONFIDENCE COGNITION ENGINE
# ==========================================
#
# FIX: Confidence was always 0.0 because it depended
# entirely on symbolic_findings (which was always []).
#
# Added stack_trace_confidence as a real signal:
# - If we parsed stack frames and mapped them to nodes
#   with high confidence → base confidence goes up.
# - If we parsed frames but couldn't map them → small boost
#   (we at least know what file/line/function failed).
# - If no stack frames at all → no boost from this signal.
#
# Also fixed the formula: dividing sum of 5 scores by 5
# meant each score was diluted to 20% of its value.
# Now: weighted sum capped at 1.0.
# ==========================================


class ConfidenceCognitionEngine:

    def __init__(
        self,
        graph,
        symbolic_findings,
        runtime_cognition,
        propagation_analysis,
        cross_file_analysis,
        stack_trace_mapping: dict | None = None,   # NEW
    ):
        self.graph                = graph or {}
        self.symbolic_findings    = symbolic_findings or []
        self.runtime_cognition    = runtime_cognition or {}
        self.propagation_analysis = propagation_analysis or {}
        self.cross_file_analysis  = cross_file_analysis or {}
        self.stack_trace_mapping  = stack_trace_mapping or {}

    def analyze_confidence(self) -> dict:

        # ---- symbolic findings ----
        symbolic_count      = len(self.symbolic_findings)
        symbolic_confidence = min(symbolic_count * 0.25, 1.0)

        # ---- propagation depth ----
        propagation_depth      = self.propagation_analysis.get("failure_propagation_depth", 0)
        propagation_confidence = min(propagation_depth * 0.15, 1.0)

        # ---- blast radius ----
        blast_radius      = self.propagation_analysis.get("blast_radius", 0)
        runtime_confidence = min(blast_radius * 0.10, 1.0)

        # ---- cross-file impact ----
        repository_impact      = len(self.cross_file_analysis.get("affected_files", []))
        repository_confidence  = min(repository_impact * 0.15, 1.0)

        # ---- execution instability bonus ----
        execution_instability = self.runtime_cognition.get("execution_instability", False)
        instability_bonus     = 0.10 if execution_instability else 0.0

        # ---- stack trace confidence (NEW) ----
        # Derived from stack_trace_mapping results.
        # High confidence frame mappings → strong signal.
        stack_trace_confidence = self._compute_stack_trace_confidence()

        # ---- weighted overall ----
        # Weights: stack_trace is strongest direct evidence,
        # symbolic findings second, rest are supporting signals.
        overall_confidence = (
            stack_trace_confidence * 0.35
            + symbolic_confidence  * 0.25
            + propagation_confidence * 0.15
            + runtime_confidence    * 0.10
            + repository_confidence * 0.10
            + instability_bonus     * 0.05
        )

        # If we have a clear error type + root cause from LLM
        # even without symbolic findings, give a minimum floor.
        if (
            self.stack_trace_mapping.get("error_type")
            and self.stack_trace_mapping.get("frame_count", 0) > 0
            and overall_confidence < 0.35
        ):
            overall_confidence = 0.35

        overall_confidence = round(min(overall_confidence, 1.0), 2)

        logger.debug(
            "Confidence: overall=%.2f stack=%.2f symbolic=%.2f",
            overall_confidence, stack_trace_confidence, symbolic_confidence
        )

        return {
            "overall_confidence":      overall_confidence,
            "symbolic_confidence":     round(symbolic_confidence, 2),
            "runtime_confidence":      round(runtime_confidence, 2),
            "propagation_confidence":  round(propagation_confidence, 2),
            "repository_confidence":   round(repository_confidence, 2),
            "stack_trace_confidence":  round(stack_trace_confidence, 2),
            "instability_bonus":       round(instability_bonus, 2),
            "confidence_factors": [
                {"factor": "symbolic_findings",    "value": symbolic_count},
                {"factor": "propagation_depth",    "value": propagation_depth},
                {"factor": "blast_radius",         "value": blast_radius},
                {"factor": "repository_impact",    "value": repository_impact},
                {"factor": "execution_instability","value": execution_instability},
                {"factor": "stack_frames_parsed",  "value": self.stack_trace_mapping.get("frame_count", 0)},
                {"factor": "stack_frames_mapped",  "value": self._mapped_frame_count()},
            ],
        }

    # ======================================
    # STACK TRACE CONFIDENCE
    # ======================================

    def _compute_stack_trace_confidence(self) -> float:
        """
        Derives confidence from stack trace mapping quality.

        - We have frames AND mapped them to graph nodes: high
        - We have frames but no graph match: medium (we still
          know exactly where the crash happened)
        - No frames parsed: 0.0
        """
        frame_count  = self.stack_trace_mapping.get("frame_count", 0)
        mapped_count = self._mapped_frame_count()
        failure_root = self.stack_trace_mapping.get("failure_root")

        if frame_count == 0:
            return 0.0

        # Base score from having parsed frames at all
        base = 0.40

        # Bonus for each mapped frame (capped)
        mapping_bonus = min(mapped_count * 0.15, 0.40)

        # Bonus for identifying a failure root
        root_bonus = 0.20 if failure_root else 0.0

        return min(base + mapping_bonus + root_bonus, 1.0)

    def _mapped_frame_count(self) -> int:
        return sum(
            1
            for f in self.stack_trace_mapping.get("mapped_frames", [])
            if f.get("matched_nodes")
        )