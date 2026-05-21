from __future__ import annotations

from app.intelligence.stack_trace_parser import parse_stack_trace

# =========================================
# LOG PARSER
# =========================================
#
# UPGRADED: The original had 4 hardcoded regex patterns:
#   python_traceback, attribute_error,
#   null_pointer, syntax_error
#
# This only covered Python and one Java exception.
# It returned a flat list of strings — no file, line,
# or function information.
#
# Now delegates to stack_trace_parser which handles
# Python, Java, JavaScript, Go, Rust, C/C++ and
# returns structured frame data.
#
# The return format is backward compatible:
#   parse_error_log() still returns a list of strings
#   so workflow_router.py needs no changes.
#
# Additionally exposes parse_error_log_structured()
# for callers that want the full ParsedTrace object.
# =========================================


def parse_error_log(error_log: str) -> list[str]:
    """
    Parse an error log and return a flat list of detected
    error/pattern names. Backward compatible with the old
    signature used by workflow_router.py.

    Returns e.g.:
        ["python_traceback", "AttributeError", "auth.py:42:login"]
    """
    if not error_log or not error_log.strip():
        return []

    parsed = parse_stack_trace(error_log)
    detected = []

    # Language-level signal
    if parsed.language and parsed.language != "unknown":
        detected.append(f"{parsed.language}_traceback")

    # Error type (e.g. "AttributeError", "NullPointerException", "panic")
    if parsed.error_type:
        detected.append(parsed.error_type)

    # One entry per frame: "file:line:function"
    for frame in parsed.frames:
        frame_sig = (
            f"{frame.file_name}"
            f":{frame.line_number or '?'}"
            f":{frame.function}"
        )
        detected.append(frame_sig)

    return detected


def parse_error_log_structured(error_log: str):
    """
    Returns the full ParsedTrace object for callers that
    need structured frame data (file, line, function per frame).

    Used by stack_trace_mapper and graph_rca_agent.
    """
    return parse_stack_trace(error_log)