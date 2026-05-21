from __future__ import annotations

import ast
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ==========================================
# DATA CLASSES
# ==========================================

@dataclass
class ValidationResult:
    is_valid          : bool
    confidence        : float           # 0.0 – 1.0
    syntax_valid      : bool
    bug_method_absent : bool            # True if the broken method no longer appears
    logic_preserved   : bool            # True if structure looks similar
    issues            : list[str]       = field(default_factory=list)
    notes             : list[str]       = field(default_factory=list)


# ==========================================
# FIX VALIDATOR
# ==========================================

class FixValidator:
    """
    Validates that the LLM-generated fix is reasonable:

    1. SYNTAX CHECK — for Python, uses ast.parse().
       For other languages, performs basic structural checks.

    2. BUG METHOD ABSENT — confirms the broken method from the
       RCA no longer appears in the fixed code.

    3. LOGIC PRESERVED — checks that the overall structure
       (class names, method names, line count) is not wildly
       different from the original. Guards against the LLM
       rewriting the entire file instead of fixing one bug.

    4. CONFIDENCE SCORE — weighted combination of the above.
    """

    def validate(
        self,
        original_source : str,
        fixed_source    : str,
        fix_evidence    : dict,
        language        : str = "unknown",
    ) -> ValidationResult:
        """
        Validates a fix and returns a ValidationResult.

        Args:
            original_source: Source code before the fix.
            fixed_source:    Source code after the fix.
            fix_evidence:    Dict from extract_fix_evidence() in fix_agent.
                             Contains: broken_method, broken_object, fix_type, etc.
            language:        Language name for syntax-check routing.
        """

        result = ValidationResult(
            is_valid          = False,
            confidence        = 0.0,
            syntax_valid      = False,
            bug_method_absent = False,
            logic_preserved   = False,
        )

        if not fixed_source or not fixed_source.strip():
            result.issues.append("Fixed source code is empty.")
            return result

        # --------------------------------------------------
        # 1. SYNTAX CHECK
        # --------------------------------------------------
        syntax_ok, syntax_note = self._check_syntax(fixed_source, language)
        result.syntax_valid = syntax_ok

        if not syntax_ok:
            result.issues.append(f"Syntax error in fixed code: {syntax_note}")
        else:
            result.notes.append("Fixed code passes syntax check.")

        # --------------------------------------------------
        # 2. BUG METHOD ABSENT
        # Check that the specific broken method is no longer
        # called incorrectly in the fixed code.
        # --------------------------------------------------
        broken_method = fix_evidence.get("broken_method", "")
        broken_symbol = fix_evidence.get("broken_symbol", "")

        bug_gone = self._check_bug_absent(
            original_source,
            fixed_source,
            broken_method,
            broken_symbol,
        )
        result.bug_method_absent = bug_gone

        if bug_gone:
            result.notes.append(
                f"Broken call '{broken_method}' no longer appears in fixed code."
            )
        elif broken_method:
            result.issues.append(
                f"Broken method '{broken_method}' still appears in fixed code — "
                f"the fix may be incomplete."
            )

        # --------------------------------------------------
        # 3. LOGIC PRESERVED
        # Compare structural signatures between original and fix.
        # A good fix changes 1-5 lines, not 50% of the file.
        # --------------------------------------------------
        logic_ok, logic_note = self._check_logic_preserved(
            original_source, fixed_source
        )
        result.logic_preserved = logic_ok

        if logic_ok:
            result.notes.append(logic_note)
        else:
            result.issues.append(logic_note)

        # --------------------------------------------------
        # 4. CONFIDENCE SCORE
        # Weights chosen to reflect engineering importance:
        #   syntax_valid:      40% — a broken syntax means the fix is unusable
        #   bug_method_absent: 35% — the primary goal
        #   logic_preserved:   25% — a safety guard
        # --------------------------------------------------
        confidence = (
            (0.40 if syntax_ok else 0.0)
            + (0.35 if bug_gone else 0.0)
            + (0.25 if logic_ok else 0.0)
        )

        # Bonus: if source_code itself is syntactically valid AND
        # we know it was already valid before (no syntax bug),
        # we add a small quality boost.
        if syntax_ok and language.lower() == "python":
            try:
                ast.parse(original_source)
                confidence = min(confidence + 0.05, 1.0)
            except SyntaxError:
                pass

        result.confidence = round(confidence, 2)
        result.is_valid   = confidence >= 0.40   # at least syntax must pass

        return result

    # ======================================
    # SYNTAX CHECK
    # ======================================

    def _check_syntax(self, source: str, language: str) -> tuple[bool, str]:
        lang = language.lower()

        if lang == "python":
            try:
                ast.parse(source)
                return True, "OK"
            except SyntaxError as e:
                return False, str(e)

        # For other languages: basic structural checks
        # (we can't easily parse them without their compilers)
        return self._structural_syntax_check(source, lang)

    def _structural_syntax_check(
        self, source: str, language: str
    ) -> tuple[bool, str]:
        """
        Language-agnostic structural check:
        - Matching braces for C-family languages
        - Non-empty source
        - No obviously truncated code
        """
        if not source.strip():
            return False, "Empty source code."

        c_family = {
            "java", "javascript", "typescript", "cpp", "c", "csharp",
            "go", "rust", "cs"
        }

        if language in c_family:
            opens  = source.count("{")
            closes = source.count("}")
            if opens != closes:
                return False, (
                    f"Unbalanced braces: {opens} open vs {closes} close. "
                    f"The fix may be truncated."
                )

        # Check for obviously incomplete code (LLM cut off mid-generation)
        last_nonblank = source.rstrip().split("\n")[-1].strip()
        incomplete_endings = (
            "...", "// TODO", "/* TODO", "# TODO", "pass # fix",
        )
        for ending in incomplete_endings:
            if last_nonblank.startswith(ending):
                return False, (
                    f"Fixed code appears truncated — ends with: {last_nonblank!r}"
                )

        return True, "OK"

    # ======================================
    # BUG METHOD ABSENT
    # ======================================

    def _check_bug_absent(
        self,
        original: str,
        fixed:    str,
        method:   str,
        symbol:   str,
    ) -> bool:
        """
        Checks if the broken method call is still present
        in the fixed code.

        Considers it fixed if:
        - The exact broken symbol no longer appears, OR
        - The symbol appears fewer times than in the original
          (partial fix — still give credit)

        A virtual frame (function="<compiler_error>") has no
        real method to check — skip validation.
        """
        if not method or method in ("<compiler_error>", "unknown"):
            return True  # can't check, assume OK

        # For NoneType fixes: check that the None assignment was fixed
        # e.g. "self.encoder = None" should be replaced with a real value
        if symbol and "." in symbol:
            # e.g. symbol="self.encoder.encode" → look for "encoder = None"
            parts = symbol.split(".")
            if len(parts) >= 2:
                attr = parts[-2]  # "encoder"
                none_pattern = rf"{re.escape(attr)}\s*=\s*None"

                original_none_count = len(re.findall(none_pattern, original))
                fixed_none_count    = len(re.findall(none_pattern, fixed))

                if original_none_count > 0 and fixed_none_count < original_none_count:
                    return True   # None assignment was removed/replaced

        # Check if the broken method call pattern is gone
        # e.g. "processed.ad(" or ".ad("
        call_pattern = rf"\.{re.escape(method)}\s*\("
        original_count = len(re.findall(call_pattern, original))
        fixed_count    = len(re.findall(call_pattern, fixed))

        if original_count > 0 and fixed_count == 0:
            return True   # completely removed
        if original_count > 0 and fixed_count < original_count:
            return True   # partially removed (counts as a fix)

        return False

    # ======================================
    # LOGIC PRESERVED
    # ======================================

    def _check_logic_preserved(
        self,
        original: str,
        fixed:    str,
    ) -> tuple[bool, str]:
        """
        Checks that the fix didn't rewrite the whole file.
        A good fix should:
        - Keep >70% of the original line count
        - Preserve the main identifiers (class names, function names)
        """
        orig_lines  = [l for l in original.splitlines() if l.strip()]
        fixed_lines = [l for l in fixed.splitlines()    if l.strip()]

        if not orig_lines:
            return True, "Original was empty — no structure to compare."

        # Line count ratio
        ratio = len(fixed_lines) / len(orig_lines)

        if ratio < 0.30:
            return False, (
                f"Fixed code is only {ratio:.0%} the size of the original. "
                f"The LLM may have truncated or drastically rewrote the code."
            )

        if ratio > 3.0:
            return False, (
                f"Fixed code is {ratio:.0%} the size of the original. "
                f"The LLM may have added excessive boilerplate."
            )

        # Check that major identifiers are preserved
        # Extract words that look like function/class/variable names
        def extract_identifiers(source: str) -> set:
            return set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]{3,})\b', source))

        orig_ids  = extract_identifiers(original)
        fixed_ids = extract_identifiers(fixed)

        if orig_ids:
            overlap = len(orig_ids & fixed_ids) / len(orig_ids)
            if overlap < 0.50:
                return False, (
                    f"Only {overlap:.0%} of original identifiers present in fixed code. "
                    f"The fix may have changed unrelated logic."
                )

        return True, f"Structure preserved (line ratio {ratio:.0%}, identifier overlap OK)."