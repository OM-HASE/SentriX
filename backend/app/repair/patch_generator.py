from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ==========================================
# DATA CLASSES
# ==========================================

@dataclass
class LineChange:
    """
    Represents a single changed line in the fix.
    """
    line_number_original : int | None
    line_number_fixed    : int | None
    change_type          : str           # "modified" | "added" | "removed"
    original_line        : str
    fixed_line           : str
    reason               : str = ""


@dataclass
class PatchResult:
    """
    Complete patch result from the generator.
    """
    unified_diff   : str              # standard --- +++ diff format
    changes        : list[LineChange] = field(default_factory=list)
    lines_added    : int = 0
    lines_removed  : int = 0
    lines_modified : int = 0
    is_empty       : bool = True      # True if no changes were made


# ==========================================
# PATCH GENERATOR
# ==========================================

class PatchGenerator:
    """
    Generates unified diffs and structured change summaries
    from original → fixed source code pairs.

    Supports any language — operates on text lines only.
    """

    def generate(
        self,
        original_source: str,
        fixed_source:    str,
        filename:        str = "source_file",
    ) -> PatchResult:
        # Normalize literal \n (backslash+n) to actual newlines.
        # When source_code is sent via JSON as "line1\nline2", Pydantic
        # may receive it as the two-character sequence backslash+n.
        # splitlines() on that string returns ONE element (the whole file).
        # difflib then sees 1 original line vs N fixed lines → bloated diff.
        original_source = self._normalize_newlines(original_source)
        fixed_source    = self._normalize_newlines(fixed_source)

        """
        Produces a PatchResult comparing original_source to fixed_source.

        Args:
            original_source: The source code before the fix.
            fixed_source:    The source code after the fix.
            filename:        Used as the file label in the unified diff header.

        Returns:
            PatchResult with unified_diff, changes[], and summary counts.
        """

        if not original_source and not fixed_source:
            return PatchResult(unified_diff="", is_empty=True)

        original_lines = (original_source or "").splitlines(keepends=True)
        fixed_lines    = (fixed_source    or "").splitlines(keepends=True)

        # --------------------------------------------------
        # UNIFIED DIFF
        # --------------------------------------------------
        diff_lines = list(difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile  = f"a/{filename}",
            tofile    = f"b/{filename}",
            lineterm  = "",
        ))

        unified_diff = "\n".join(diff_lines)
        is_empty     = len(diff_lines) == 0

        if is_empty:
            logger.debug("PatchGenerator: no changes detected.")
            return PatchResult(unified_diff="", is_empty=True)

        # --------------------------------------------------
        # STRUCTURED CHANGE SUMMARY
        # Match changed lines from the SequenceMatcher so we
        # can report (original_line, fixed_line, type) pairs.
        # --------------------------------------------------
        changes: list[LineChange] = []
        lines_added    = 0
        lines_removed  = 0
        lines_modified = 0

        matcher = difflib.SequenceMatcher(
            None,
            original_lines,
            fixed_lines,
            autojunk=False,
        )

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            elif tag == "replace":
                # Try to pair up modified lines 1-to-1 where possible
                orig_block = original_lines[i1:i2]
                fixed_block = fixed_lines[j1:j2]
                max_pairs = max(len(orig_block), len(fixed_block))

                for k in range(max_pairs):
                    orig_line  = orig_block[k].rstrip("\n") if k < len(orig_block) else ""
                    fixed_line = fixed_block[k].rstrip("\n") if k < len(fixed_block) else ""

                    if k < len(orig_block) and k < len(fixed_block):
                        change_type = "modified"
                        lines_modified += 1
                    elif k < len(fixed_block):
                        change_type = "added"
                        lines_added += 1
                    else:
                        change_type = "removed"
                        lines_removed += 1

                    changes.append(LineChange(
                        line_number_original = (i1 + k + 1) if k < len(orig_block) else None,
                        line_number_fixed    = (j1 + k + 1) if k < len(fixed_block) else None,
                        change_type          = change_type,
                        original_line        = orig_line,
                        fixed_line           = fixed_line,
                    ))

            elif tag == "insert":
                for k, line in enumerate(fixed_lines[j1:j2]):
                    changes.append(LineChange(
                        line_number_original = None,
                        line_number_fixed    = j1 + k + 1,
                        change_type          = "added",
                        original_line        = "",
                        fixed_line           = line.rstrip("\n"),
                    ))
                    lines_added += 1

            elif tag == "delete":
                for k, line in enumerate(original_lines[i1:i2]):
                    changes.append(LineChange(
                        line_number_original = i1 + k + 1,
                        line_number_fixed    = None,
                        change_type          = "removed",
                        original_line        = line.rstrip("\n"),
                        fixed_line           = "",
                    ))
                    lines_removed += 1

        logger.debug(
            "PatchGenerator: +%d -%d ~%d lines changed.",
            lines_added, lines_removed, lines_modified
        )

        return PatchResult(
            unified_diff   = unified_diff,
            changes        = changes,
            lines_added    = lines_added,
            lines_removed  = lines_removed,
            lines_modified = lines_modified,
            is_empty       = False,
        )

    def _normalize_newlines(self, source: str) -> str:
        """
        If source has no real newlines but has literal \\n sequences,
        convert them. Handles both JSON-escaped strings and raw strings.
        """
        if source and '\n' not in source:
            if '\\n' in source:
                source = source.replace('\\n', '\n')
            elif r'\n' in source:
                source = source.replace(r'\n', '\n')
        return source

    def to_dict(self, patch: PatchResult) -> dict:
        """
        Serializes a PatchResult to a plain dict for API responses.
        """
        return {
            "unified_diff":    patch.unified_diff,
            "lines_added":     patch.lines_added,
            "lines_removed":   patch.lines_removed,
            "lines_modified":  patch.lines_modified,
            "is_empty":        patch.is_empty,
            "changes": [
                {
                    "line_original": c.line_number_original,
                    "line_fixed":    c.line_number_fixed,
                    "type":          c.change_type,
                    "original":      c.original_line,
                    "fixed":         c.fixed_line,
                    "reason":        c.reason,
                }
                for c in patch.changes
            ],
        }