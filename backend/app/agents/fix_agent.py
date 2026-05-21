from __future__ import annotations

import json
import uuid
import re
import logging

import ollama

from app.repair.patch_generator import PatchGenerator
from app.repair.fix_validator   import FixValidator

logger = logging.getLogger(__name__)

_patch_generator = PatchGenerator()
_fix_validator   = FixValidator()


# ==========================================
# FIX TYPES
# ==========================================

FIX_TYPE_LABELS = {
    "none_type_method_call": "null_initialization",
    "unresolved_method":     "method_correction",
    "CompileError_UnresolvedMember":  "method_correction",
    "CompileError_UnresolvedMethod":  "method_correction",
    "CompileError_Undefined":         "undefined_identifier",
    "CompileError_UndeclaredIdentifier": "undefined_identifier",
    "CompileError_UndefinedReference":   "linker_error",
    # lowercase versions (internal)
    "attribute_error":       "null_initialization",
    "null_dereference_failure": "null_initialization",
    "import_error":          "import_fix",
    "type_error":            "type_fix",
    "runtime_failure":       "general_fix",
    # PascalCase versions (from LLM / stack trace parser)
    "AttributeError":        "null_initialization",
    "NullPointerException":  "null_initialization",
    "NullReferenceException":"null_initialization",
    "TypeError":             "type_fix",
    "ImportError":           "import_fix",
    "ModuleNotFoundError":   "import_fix",
    "NameError":             "undefined_identifier",
    "CompileError_UnresolvedMember": "method_correction",
}


# ==========================================
# PUBLIC API
# ==========================================

def generate_fix(
    source_code   : str,
    rca_result    : dict | None = None,
    error_log     : str         = "",
    language      : str         = "",
    filename      : str         = "source_file",
) -> dict:
    """
    Main entry point for the Fix Agent.

    Takes source code + RCA result (or just error log if no RCA)
    and returns a structured fix with unified diff, changes,
    explanation, and confidence score.

    Args:
        source_code:  The original source code to fix.
        rca_result:   The output from /api/rca (optional but preferred).
                      If not provided, runs lightweight evidence extraction
                      directly from the error log.
        error_log:    Raw error or compiler output (optional).
        language:     Language hint (auto-detected if not provided).
        filename:     Used in the unified diff header.

    Returns:
        Dict with: fix_id, language, fix_type, fixed_source_code,
                   unified_diff, changes, explanation, confidence,
                   validation, patch_stats
    """

    fix_id = str(uuid.uuid4())[:8]

    # Normalize literal \n to real newlines (Postman/JSON encoding issue)
    source_code = _normalize_newlines(source_code)

    # --------------------------------------------------
    # STEP 1 — EXTRACT FIX EVIDENCE
    # --------------------------------------------------
    evidence = _extract_fix_evidence(rca_result, error_log, source_code)

    detected_language = (
        language
        or evidence.get("language")
        or _detect_language_from_source(source_code)
        or "unknown"
    )

    fix_type = FIX_TYPE_LABELS.get(
        evidence.get("issue_type", ""),
        FIX_TYPE_LABELS.get(evidence.get("error_type", ""), "general_fix")
    )

    logger.info(
        "Fix Agent [%s]: language=%s fix_type=%s broken=%s",
        fix_id, detected_language, fix_type,
        evidence.get("broken_symbol", "?")
    )

    # --------------------------------------------------
    # STEP 2 — BUILD LLM PROMPT
    # --------------------------------------------------
    prompt = _build_fix_prompt(source_code, evidence, detected_language)

    # --------------------------------------------------
    # STEP 3 — CALL LLM
    # --------------------------------------------------
    raw_response = _call_ollama(prompt)

    # --------------------------------------------------
    # STEP 4 — PARSE LLM RESPONSE
    # --------------------------------------------------
    fix_data = _parse_llm_response(raw_response, source_code)

    fixed_source = fix_data.get("fixed_code", "")
    explanation  = fix_data.get("explanation", "")
    llm_changes  = fix_data.get("changes", [])

    # --------------------------------------------------
    # STEP 5 — GENERATE UNIFIED DIFF
    # --------------------------------------------------
    patch = _patch_generator.generate(source_code, fixed_source, filename)
    patch_dict = _patch_generator.to_dict(patch)

    # Enrich patch changes with LLM-provided reasons
    _enrich_changes_with_reasons(patch_dict["changes"], llm_changes)

    # --------------------------------------------------
    # STEP 6 — VALIDATE FIX
    # --------------------------------------------------
    validation = _fix_validator.validate(
        original_source = source_code,
        fixed_source    = fixed_source,
        fix_evidence    = evidence,
        language        = detected_language,
    )

    # --------------------------------------------------
    # STEP 7 — RETURN STRUCTURED RESULT
    # --------------------------------------------------
    return {
        "fix_id":           fix_id,
        "language":         detected_language,
        "fix_type":         fix_type,

        "fixed_source_code": fixed_source,

        "unified_diff":    patch_dict["unified_diff"],
        "patch_stats": {
            "lines_added":    patch_dict["lines_added"],
            "lines_removed":  patch_dict["lines_removed"],
            "lines_modified": patch_dict["lines_modified"],
            "is_empty":       patch_dict["is_empty"],
        },
        "changes": patch_dict["changes"],

        "explanation": explanation,

        "confidence": validation.confidence,
        "validation": {
            "is_valid":          validation.is_valid,
            "syntax_valid":      validation.syntax_valid,
            "bug_method_absent": validation.bug_method_absent,
            "logic_preserved":   validation.logic_preserved,
            "issues":            validation.issues,
            "notes":             validation.notes,
        },

        "fix_evidence": {
            "broken_method": evidence.get("broken_method", ""),
            "broken_object": evidence.get("broken_object", ""),
            "broken_symbol": evidence.get("broken_symbol", ""),
            "root_cause":    evidence.get("root_cause", ""),
            "repair_hint":   evidence.get("repair_hint", ""),
        },
    }


# ==========================================
# STEP 1: EXTRACT FIX EVIDENCE
# ==========================================

def _extract_fix_evidence(
    rca_result : dict | None,
    error_log  : str,
    source_code: str,
) -> dict:
    """
    Extracts focused fixing evidence from the RCA result or error log.

    Priority order:
      1. none_type_method_call findings (most specific)
      2. unresolved_method findings (second most specific)
      3. stack_trace_mapping failure_root
      4. root_cause summary
      5. raw error_log keywords
    """
    evidence: dict = {}

    if not rca_result:
        return _extract_from_error_log(error_log)

    # --- stack trace language ---
    st = rca_result.get("stack_trace_mapping") or {}
    evidence["language"]      = st.get("language", "")
    evidence["error_type"]    = st.get("error_type", "")
    evidence["error_message"] = st.get("error_message", "")

    # --- failure root (most precise signal) ---
    failure_root = st.get("failure_root") or {}
    evidence["failure_file"] = failure_root.get("file", "")
    evidence["failure_line"] = failure_root.get("line")
    failure_func = failure_root.get("function", "")

    # Priority fix: use the EXACT broken function from stack trace
    # This is more reliable than the first symbolic finding because
    # symbolic_findings may contain field accesses (orderId, amount)
    # while the stack trace pinpoints the actual broken call (ad, puhs, calculte)
    safe_funcs = {"<compiler_error>", "unknown", "encode", ""}
    if failure_func and failure_func not in safe_funcs:
        evidence["broken_method"] = failure_func
        evidence["broken_symbol"] = failure_func
        evidence["issue_type"]    = "unresolved_method"

    evidence["failure_func"] = failure_func

    # --- symbolic findings (pick most critical) ---
    findings = rca_result.get("symbolic_findings") or []
    issue_types = rca_result.get("incident", {})
    evidence["issue_type"] = issue_types.get("error_type", "")

    # Priority: none_type > unresolved_method > others
    priority = {"none_type_method_call": 0, "unresolved_method": 1}
    findings_sorted = sorted(
        findings,
        key=lambda f: priority.get(f.get("issue_type", ""), 99)
    )

    if findings_sorted:
        top = findings_sorted[0]
        evidence["broken_method"] = top.get("method", "")
        evidence["broken_object"] = top.get("object", "")
        evidence["broken_symbol"] = top.get("symbol", "") or top.get("called_as", "")
        evidence["issue_type"]    = top.get("issue_type", "")
        evidence["none_assigned"] = top.get("none_assigned", False)

        # Get the repair plan from the finding if available
        repair = top.get("repair_plan") or {}
        evidence["repair_hint"] = (
            repair.get("suggested_action")
            or (f"Replace with '{repair.get('suggested_symbol')}'" if repair.get("suggested_symbol") else "")
        )

        # Get nearest match (correct method name)
        evidence["nearest_match"] = top.get("nearest_match", "")

    # --- root cause summary ---
    evidence["root_cause"] = (
        (rca_result.get("root_cause") or {}).get("summary", "")
    )

    # --- repair plan from LLM reasoning ---
    rp = (rca_result.get("repair_plan") or {}).get("recommended_fix", "")
    if rp and not evidence.get("repair_hint"):
        # Take first 300 chars of repair plan as the hint
        evidence["repair_hint"] = rp[:300]

    return evidence


def _extract_from_error_log(error_log: str) -> dict:
    """
    Fallback: extract evidence directly from the error log
    when no RCA result is provided.
    """
    evidence: dict = {}

    if not error_log:
        return evidence

    # AttributeError: 'X' has no attribute 'Y'
    m = re.search(r"has no attribute ['\"](\w+)['\"]", error_log)
    if m:
        evidence["broken_method"] = m.group(1)
        evidence["broken_symbol"] = m.group(1)
        evidence["issue_type"]    = "unresolved_method"

    # "X is not a function"
    m2 = re.search(r"(\w+) is not a function", error_log)
    if m2:
        evidence["broken_method"] = m2.group(1)
        evidence["broken_symbol"] = m2.group(1)
        evidence["issue_type"]    = "unresolved_method"

    # "method X(Y)" — Java/compiler
    m3 = re.search(r"method\s+(\w+)\s*\(", error_log)
    if m3:
        evidence["broken_method"] = m3.group(1)
        evidence["broken_symbol"] = m3.group(1)

    # "no method named `X`" — Rust
    m4 = re.search(r"no method named `(\w+)`", error_log)
    if m4:
        evidence["broken_method"] = m4.group(1)
        evidence["broken_symbol"] = m4.group(1)
        evidence["issue_type"]    = "CompileError_UnresolvedMethod"

    # "has no member named 'X'" — C++
    m5 = re.search(r"has no member named ['\"](\w+)['\"]", error_log)
    if m5:
        evidence["broken_method"] = m5.group(1)
        evidence["broken_symbol"] = m5.group(1)
        evidence["issue_type"]    = "CompileError_UnresolvedMember"

    # "does not contain a definition for 'X'" — C#
    m6 = re.search(r"does not contain a definition for '(\w+)'", error_log)
    if m6:
        evidence["broken_method"] = m6.group(1)
        evidence["broken_symbol"] = m6.group(1)
        evidence["issue_type"]    = "CompileError_UnresolvedMember"

    # Generic error type
    et = re.search(r'\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Fault))\b', error_log)
    if et:
        evidence["error_type"] = et.group(1)

    return evidence


# ==========================================
# STEP 2: BUILD PROMPT
# ==========================================

def _build_fix_prompt(
    source_code: str,
    evidence:    dict,
    language:    str,
) -> str:
    """
    Builds a focused, evidence-grounded LLM prompt for fix generation.

    Key principles:
    - Show ONLY the specific evidence, not the full RCA dump
    - Ask for JSON output (easier to parse than prose)
    - Strongly instruct "fix ONLY the specific bug"
    - Include the repair hint if available
    """

    broken_method = evidence.get("broken_method", "")
    broken_symbol = evidence.get("broken_symbol", "")
    broken_object = evidence.get("broken_object", "")
    root_cause    = evidence.get("root_cause", "")
    repair_hint   = evidence.get("repair_hint", "")
    nearest_match = evidence.get("nearest_match", "")
    issue_type    = evidence.get("issue_type", "")
    none_assigned = evidence.get("none_assigned", False)
    error_type    = evidence.get("error_type", "")
    error_message = evidence.get("error_message", "")

    # Truncate large source code to keep prompt focused
    sc = source_code
    if len(sc) > 2000:
        sc = sc[:2000] + "\n... [truncated — fix only the identified bug above]"

    # Build specific instruction based on issue type
    if issue_type == "none_type_method_call" or none_assigned:
        specific_instruction = (
            f"self.{broken_object.replace('self.', '')} is assigned None in __init__. "
            f"Fix it by initializing it with a proper value before .{broken_method}() is called."
        )
    elif issue_type in (
        "unresolved_method",
        "CompileError_UnresolvedMember",
        "CompileError_UnresolvedMethod"
    ):
        if nearest_match:
            specific_instruction = (
                f"The method .{broken_method}() does not exist. "
                f"The correct method is probably .{nearest_match}(). Replace it."
            )
        else:
            specific_instruction = (
                f"The method .{broken_method}() does not exist on {broken_object}. "
                f"Find the correct method and replace it."
            )
    else:
        specific_instruction = root_cause or f"Fix the {error_type}: {error_message}"

    if repair_hint:
        specific_instruction += f"\n\nRepair suggestion: {repair_hint}"

    # Language-specific overrides for common patterns
    lang_lower = language.lower()
    if lang_lower == "go" and broken_method:
        specific_instruction += (
            "\n\nIMPORTANT Go rule: Go slices/maps have NO methods. "
            f"Replace `variable.{broken_method}(value)` with "
            f"`variable = append(variable, value)` — do NOT comment it out, "
            "the feature should still work with the correct syntax."
        )
    elif lang_lower in ("javascript", "typescript") and broken_method:
        specific_instruction += (
            f"\n\nIMPORTANT: The broken call `.{broken_method}()` is a typo. "
            "Find the one line with this typo and replace it with the correct "
            "Array method name. Do NOT change any other lines."
        )

    prompt = f"""You are an expert {language} software engineer fixing a specific bug.

BUG IDENTIFIED:
Error type     : {error_type or issue_type}
Broken call    : {broken_symbol}
Root cause     : {root_cause or error_message}

SPECIFIC FIX INSTRUCTION:
{specific_instruction}

RULES:
1. Fix ONLY the specific bug above — do NOT change any other logic
2. Do NOT add comments explaining the fix
3. Do NOT add imports that are not needed
4. Do NOT rewrite functions that are unrelated to the bug
5. Return the COMPLETE source file with the fix applied

ORIGINAL SOURCE CODE:
{sc}

RETURN ONLY THIS JSON (no markdown, no backticks, no explanation outside JSON):
{{
    "fixed_code": "complete fixed source code here",
    "explanation": "one sentence: what line changed and why",
    "changes": [
        {{
            "original_line": "the exact original broken line",
            "fixed_line": "the exact fixed replacement line",
            "reason": "brief reason"
        }}
    ]
}}"""

    return prompt


# ==========================================
# STEP 3: CALL OLLAMA
# ==========================================

def _call_ollama(prompt: str) -> str:
    """
    Calls Ollama with the fix prompt.
    Uses temperature=0.05 for deterministic fixes.
    Higher num_predict than RCA to allow full code output.
    """
    try:
        response = ollama.chat(
            model="qwen2.5-coder:7b",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": 0.05,
                "top_p":       0.90,
                "num_predict": 2000,  # higher than RCA — needs to return full file
            }
        )
        return response["message"]["content"]

    except Exception as exc:
        logger.error("Ollama call failed in fix_agent: %s", exc)
        return ""


# ==========================================
# STEP 4: PARSE LLM RESPONSE
# ==========================================

def _parse_llm_response(
    raw: str,
    original_source: str,
) -> dict:
    """
    Parses the LLM response into {fixed_code, explanation, changes}.

    Handles cases where the LLM:
    - Returns clean JSON                    → parse directly
    - Wraps JSON in markdown ```json...```  → strip fences
    - Returns prose + JSON                  → find the JSON block
    - Fails to return valid JSON            → use original source as fallback
    """

    if not raw or not raw.strip():
        logger.warning("fix_agent: LLM returned empty response. Using original source.")
        return {
            "fixed_code":  original_source,
            "explanation": "LLM returned empty response — no fix applied.",
            "changes":     [],
        }

    # --- strip markdown code fences if present ---
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # --- find JSON object boundaries ---
    first_brace = cleaned.find("{")
    last_brace  = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = cleaned[first_brace:last_brace + 1]
    else:
        json_str = cleaned

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # LLM didn't return valid JSON — try to extract "fixed_code" manually
        logger.warning(
            "fix_agent: LLM response is not valid JSON. "
            "Attempting manual extraction."
        )
        data = _manual_extract(cleaned, original_source)

    # Ensure required fields exist
    fixed_code = data.get("fixed_code") or original_source
    explanation = data.get("explanation") or "Fix applied."
    changes     = data.get("changes") or []

    # --- validate fixed_code is non-empty string ---
    if not isinstance(fixed_code, str) or not fixed_code.strip():
        logger.warning(
            "fix_agent: LLM returned empty 'fixed_code'. Using original."
        )
        fixed_code = original_source
        explanation = "LLM did not return valid fixed code — no changes applied."

    return {
        "fixed_code":  fixed_code,
        "explanation": explanation,
        "changes":     changes if isinstance(changes, list) else [],
    }


def _manual_extract(text: str, fallback: str) -> dict:
    """
    Last-resort extraction when JSON parsing fails completely.
    Tries to find a code block inside the LLM response.
    """
    # Look for content between "fixed_code": " and the next "
    # (handles cases where only the string was not properly escaped)
    code_match = re.search(
        r'"fixed_code"\s*:\s*"(.*?)"\s*[,}]',
        text,
        re.DOTALL
    )
    if code_match:
        raw_code = code_match.group(1)
        # Unescape common JSON string escapes
        code = raw_code.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        return {
            "fixed_code":  code,
            "explanation": "Partial parse — JSON was malformed.",
            "changes":     [],
        }

    return {
        "fixed_code":  fallback,
        "explanation": "Could not parse LLM response — no fix applied.",
        "changes":     [],
    }


# ==========================================
# STEP 5: ENRICH CHANGES
# ==========================================

def _enrich_changes_with_reasons(
    patch_changes: list[dict],
    llm_changes:   list[dict],
) -> None:
    """
    Enriches patch_changes in-place with reason strings from
    the LLM-provided changes list, matched by original_line content.
    """
    if not llm_changes:
        return

    # Build a lookup: original_line_text → reason
    reason_map: dict[str, str] = {}
    for lc in llm_changes:
        orig = (lc.get("original_line") or "").strip()
        reason = lc.get("reason") or ""
        if orig and reason:
            reason_map[orig] = reason

    for change in patch_changes:
        orig = (change.get("original") or "").strip()
        if orig in reason_map:
            change["reason"] = reason_map[orig]


# ==========================================
# UTILITY
# ==========================================

def _normalize_newlines(source: str) -> str:
    """
    Convert literal backslash-n sequences to real newlines.
    Postman often sends JSON with \\n which JSON-decodes to backslash+n,
    not an actual newline character.
    """
    if not source:
        return source
    # Already has real newlines → fine
    if "\n" in source:
        return source
    # Has literal backslash+n → convert
    if "\\n" in source:
        return source.replace("\\n", "\n")
    return source


def _detect_language_from_source(source: str) -> str:
    """
    Simple heuristic language detection from source code.
    Used as last resort when language is not provided.
    """
    if not source:
        return "unknown"

    src = source[:500].lower()

    if "def " in src and ("import " in src or "self" in src):
        return "python"
    if "public class " in src or "system.out.println" in src:
        return "java"
    if "console.log" in src or "function " in src or "const " in src or "=> {" in src:
        return "javascript"
    if "#include" in src and ("std::" in src or "cout" in src):
        return "cpp"
    if "package main" in src or "fmt.println" in src:
        return "go"
    if "fn main()" in src or "let mut " in src:
        return "rust"
    if "using system" in src or "console.writeline" in src.lower():
        return "csharp"
    if '#include<stdio.h>' in src or 'printf(' in src:
        return "c"

    return "unknown"