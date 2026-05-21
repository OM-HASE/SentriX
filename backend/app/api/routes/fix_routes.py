from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.fix_agent import generate_fix
from app.agents.graph_rca_agent import analyze_graph_root_cause
from app.graph.graph_builder import build_repository_graph
from app.graph.graph_memory import repository_graph_memory

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================
# SCHEMAS
# ==========================================

class FixRequest(BaseModel):
    """
    Request body for POST /api/fix.

    Two usage modes:

    MODE A — Fix with pre-computed RCA (recommended):
        Provide source_code + rca_result from a previous /api/rca call.
        The fix agent uses the RCA evidence directly — faster and more precise.

    MODE B — Fix with just error log (no RCA):
        Provide source_code + error_log.
        The fix agent extracts evidence from the error log and fixes directly.
        Use this for quick one-shot fixes when you don't need a full RCA report.

    Optional fields:
        language : language hint — auto-detected if omitted
        filename : shown in the unified diff header (e.g. "auth.py")
    """
    source_code : str
    error_log   : str  | None = None
    rca_result  : dict | None = None
    language    : str  | None = None
    filename    : str  | None = None


class FixAndRCARequest(BaseModel):
    """
    Request body for POST /api/fix-and-rca.

    Runs the full RCA pipeline first, then immediately generates
    a fix. Returns both the RCA report and the fix in one call.

    Use this when you want everything in one request.
    """
    source_code : str
    error_log   : str | None = None
    language    : str | None = None
    filename    : str | None = None


# ==========================================
# POST /api/fix
# ==========================================

@router.post("/fix")
async def fix_code(data: FixRequest) -> dict:
    """
    Generates a fix for the identified bug.

    Requires either:
      - rca_result (from /api/rca) — uses pre-computed evidence
      - error_log — extracts evidence from the error log directly

    Returns:
      fix_id, language, fix_type, fixed_source_code,
      unified_diff, changes[], explanation, confidence, validation
    """

    if not data.source_code or not data.source_code.strip():
        raise HTTPException(
            status_code=422,
            detail="source_code is required and must not be empty."
        )

    if not data.rca_result and not data.error_log:
        raise HTTPException(
            status_code=422,
            detail=(
                "Provide either rca_result (from POST /api/rca) "
                "or error_log to guide the fix."
            )
        )

    # Extract rca_result from wrapper if needed
    # /api/rca returns {"mode": ..., "rca": {...}}
    # /api/graph-rca returns {"graph_rca": {...}}
    rca = data.rca_result
    if rca:
        if "rca" in rca:
            rca = rca["rca"]
        elif "graph_rca" in rca:
            rca = rca["graph_rca"]

    filename = data.filename or _guess_filename(data.language, data.source_code)

    try:
        result = generate_fix(
            source_code = data.source_code,
            rca_result  = rca,
            error_log   = data.error_log or "",
            language    = data.language  or "",
            filename    = filename,
        )
    except Exception as exc:
        logger.error("Fix agent failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fix agent encountered an error: {str(exc)}"
        )

    return {"fix": result}


# ==========================================
# POST /api/fix-and-rca
# ==========================================

@router.post("/fix-and-rca")
async def fix_and_rca(data: FixAndRCARequest) -> dict:
    """
    One-shot endpoint: runs full RCA then immediately generates a fix.

    Equivalent to calling POST /api/rca then POST /api/fix,
    but in a single request for convenience.

    Returns both the full RCA report and the fix result.
    """

    if not data.source_code or not data.source_code.strip():
        raise HTTPException(
            status_code=422,
            detail="source_code is required."
        )

    if not data.error_log:
        raise HTTPException(
            status_code=422,
            detail="error_log is required for /api/fix-and-rca."
        )

    # --- Run RCA ---
    try:
        build_repository_graph(data.source_code)
        rca_result = analyze_graph_root_cause(
            error_log   = data.error_log,
            source_code = data.source_code,
        )
    except Exception as exc:
        logger.error("RCA failed in fix-and-rca: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"RCA pipeline failed: {str(exc)}"
        )

    # --- Generate Fix using RCA evidence ---
    filename = data.filename or _guess_filename(data.language, data.source_code)

    try:
        fix_result = generate_fix(
            source_code = data.source_code,
            rca_result  = rca_result,
            error_log   = data.error_log,
            language    = data.language or rca_result.get("stack_trace_mapping", {}).get("language", ""),
            filename    = filename,
        )
    except Exception as exc:
        logger.error("Fix agent failed in fix-and-rca: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fix agent failed: {str(exc)}"
        )

    return {
        "rca": rca_result,
        "fix": fix_result,
    }


# ==========================================
# UTILITY
# ==========================================

def _guess_filename(language: str | None, source_code: str) -> str:
    """
    Guesses a reasonable filename for the unified diff header
    when none is provided.
    """
    lang = (language or "").lower()
    ext_map = {
        "python":     "main.py",
        "java":       "Main.java",
        "javascript": "main.js",
        "typescript": "main.ts",
        "cpp":        "main.cpp",
        "c":          "main.c",
        "go":         "main.go",
        "rust":       "main.rs",
        "csharp":     "Program.cs",
    }

    if lang in ext_map:
        return ext_map[lang]

    # Try to infer from source
    if "package main" in source_code:
        return "main.go"
    if "fn main()" in source_code:
        return "main.rs"
    if "public class " in source_code:
        # Try to extract class name
        import re
        m = re.search(r"public class (\w+)", source_code)
        if m:
            return f"{m.group(1)}.java"
        return "Main.java"
    if "using System" in source_code:
        return "Program.cs"
    if "def " in source_code or "import " in source_code:
        return "main.py"

    return "source_file.txt"