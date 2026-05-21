from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ==========================================
# STACK FRAME / PARSED TRACE
# ==========================================

@dataclass
class StackFrame:
    file_path  : str
    file_name  : str
    line_number: object   # int or None
    function   : str
    language   : str
    raw_line   : str


@dataclass
class ParsedTrace:
    frames         : list  = field(default_factory=list)
    error_type     : str   = ""
    error_message  : str   = ""
    language       : str   = "unknown"
    raw_log        : str   = ""


# ==========================================
# LANGUAGE PATTERNS
# ==========================================

_PYTHON_FRAME = re.compile(
    r'File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+),\s+in\s+(?P<func>\S+)',
    re.MULTILINE
)
_PYTHON_ERROR = re.compile(
    r'^(?P<etype>[A-Za-z][A-Za-z0-9_]*(?:Error|Exception|Warning|Interrupt|Exit|Fault|Stop))'
    r'(?::\s*(?P<msg>.+))?$',
    re.MULTILINE
)

_JAVA_FRAME = re.compile(
    r'at\s+(?:[\w.$]+\.)*(?P<func>[\w$<>]+)\('
    r'(?P<file>[A-Za-z0-9_$]+\.java):(?P<line>\d+)\)',
    re.MULTILINE
)
_JAVA_ERROR = re.compile(
    r'^(?P<etype>(?:[\w.]+\.)?[A-Z][A-Za-z0-9_$]*(?:Exception|Error|Throwable|Fault))'
    r'(?::\s*(?P<msg>.+))?$',
    re.MULTILINE
)

_JS_FRAME = re.compile(
    r'at\s+(?:(?P<func>[\w.<>$\[\] /]+)\s+\()?'
    r'(?P<file>[^()\s:]+\.(?:js|ts|jsx|tsx|mjs|cjs))'
    r':(?P<line>\d+)(?::\d+)?\)?',
    re.MULTILINE
)
_JS_ERROR = re.compile(
    r'^(?P<etype>[A-Z][A-Za-z0-9_]*(?:Error|Exception))'
    r'(?::\s*(?P<msg>.+))?$',
    re.MULTILINE
)

_GO_FRAME_FILE = re.compile(r'^\s+(?P<file>[^\s]+\.go):(?P<line>\d+)', re.MULTILINE)
_GO_FRAME_FUNC = re.compile(r'^(?P<func>[\w.*()[\]/]+)\(', re.MULTILINE)
_GO_ERROR      = re.compile(r'^(?:panic|fatal error|runtime error):\s*(?P<msg>.+)$', re.MULTILINE | re.IGNORECASE)

_RUST_FRAME_NUM  = re.compile(r'^\s+\d+:\s+(?P<func>.+)$', re.MULTILINE)
_RUST_FRAME_FILE = re.compile(r'at\s+(?P<file>[^\s:]+\.rs):(?P<line>\d+)', re.MULTILINE)
_RUST_ERROR      = re.compile(r'^(?:thread\s+\'.+\'\s+)?panicked at\s+\'(?P<msg>[^\']+)\'', re.MULTILINE)

_C_FRAME = re.compile(
    r'#\d+\s+(?:0x[0-9a-f]+\s+in\s+)?(?P<func>\w+)\s+\([^)]*\)'
    r'\s+at\s+(?P<file>[^\s:]+\.(?:c|cpp|cc|cxx|h|hpp)):(?P<line>\d+)',
    re.MULTILINE
)
_C_ERROR = re.compile(
    r'(?:Segmentation fault|Bus error|Aborted|Illegal instruction|double free|heap corruption)',
    re.IGNORECASE
)

# ==========================================
# MAIN PARSER
# ==========================================

def parse_stack_trace(error_log: str) -> ParsedTrace:
    """
    Parses any error log into a structured ParsedTrace.

    IMPORTANT FIX: handles two cases:
      A. Full traceback with File/line frames  (original)
      B. Single-line error with no frames      (new)
         e.g. "AttributeError: 'NoneType' object has no attribute 'encode'"

    For case B: extracts error_type + message and synthesizes
    a virtual frame from the attribute name in the message,
    so the stack_trace_mapper can still work.
    """
    if not error_log or not error_log.strip():
        return ParsedTrace(raw_log=error_log or "")

    result = ParsedTrace(raw_log=error_log)

    candidates = [
        _try_python(error_log),
        _try_java(error_log),
        _try_javascript(error_log),
        _try_go(error_log),
        _try_rust(error_log),
        _try_c(error_log),
        _try_gcc_clang(error_log),
        _try_msvc(error_log),
        _try_go_compiler(error_log),    # Go compiler errors
        _try_rust_compiler(error_log),  # Rust compiler errors
        _try_java_compiler(error_log),  # Java compiler errors
        _try_csharp(error_log),         # C# compiler/runtime errors
    ]

    best = max(candidates, key=lambda p: len(p.frames))

    if best.frames:
        result.frames        = best.frames
        result.error_type    = best.error_type
        result.error_message = best.error_message
        result.language      = best.language
    else:
        # ---- Case B: no frames found ----
        # Still try to extract error type and message.
        result.error_type = _extract_generic_error_type(error_log)
        result.language   = "unknown"

        # Try to get the message portion
        if result.error_type and ":" in error_log:
            after_colon = error_log.split(":", 1)[1].strip()
            result.error_message = after_colon.split("\n")[0].strip()

        # Synthesize a virtual frame from the error message
        # e.g. "'NoneType' has no attribute 'encode'" → function="encode"
        virtual_frame = _synthesize_frame_from_message(
            result.error_message or error_log,
            result.error_type,
        )
        if virtual_frame:
            result.frames = [virtual_frame]
            # We can guess Python if we see NoneType
            if "nonetype" in error_log.lower() or "attributeerror" in error_log.lower():
                result.language = "python"

    logger.debug(
        "Parsed %d frames, lang=%s, error=%s",
        len(result.frames), result.language, result.error_type
    )
    return result


# ==========================================
# LANGUAGE-SPECIFIC PARSERS
# ==========================================

def _try_python(log: str) -> ParsedTrace:
    frames = []
    for m in _PYTHON_FRAME.finditer(log):
        fp = m.group("file")
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=int(m.group("line")), function=m.group("func"),
            language="python", raw_line=m.group(0),
        ))
    et, em = "", ""
    e = _PYTHON_ERROR.search(log)
    if e:
        et = e.group("etype") or ""
        em = (e.group("msg") or "").strip()
    return ParsedTrace(frames=frames, error_type=et, error_message=em,
                       language="python" if frames else "")


def _try_java(log: str) -> ParsedTrace:
    frames = []
    for m in _JAVA_FRAME.finditer(log):
        frames.append(StackFrame(
            file_path=m.group("file"), file_name=m.group("file"),
            line_number=int(m.group("line")), function=m.group("func"),
            language="java", raw_line=m.group(0),
        ))
    et, em = "", ""
    e = _JAVA_ERROR.search(log)
    if e:
        et = e.group("etype") or ""
        em = (e.group("msg") or "").strip()
    return ParsedTrace(frames=frames, error_type=et, error_message=em,
                       language="java" if frames else "")


def _try_javascript(log: str) -> ParsedTrace:
    frames = []
    for m in _JS_FRAME.finditer(log):
        func = (m.group("func") or "<anonymous>").strip()
        fp   = m.group("file")
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=int(m.group("line")), function=func,
            language="javascript", raw_line=m.group(0),
        ))
    et, em = "", ""
    e = _JS_ERROR.search(log)
    if e:
        et = e.group("etype") or ""
        em = (e.group("msg") or "").strip()
    return ParsedTrace(frames=frames, error_type=et, error_message=em,
                       language="javascript" if frames else "")


def _try_go(log: str) -> ParsedTrace:
    file_matches = list(_GO_FRAME_FILE.finditer(log))
    func_matches = list(_GO_FRAME_FUNC.finditer(log))
    frames = []
    for fm in file_matches:
        fp       = fm.group("file")
        line_num = int(fm.group("line"))
        file_pos = fm.start()
        best_func, best_pos = "<unknown>", -1
        for func_m in func_matches:
            if func_m.start() < file_pos and func_m.start() > best_pos:
                best_pos  = func_m.start()
                best_func = func_m.group("func").strip()
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1],
            line_number=line_num, function=best_func,
            language="go", raw_line=fm.group(0),
        ))
    et, em = "panic", ""
    e = _GO_ERROR.search(log)
    if e:
        em = (e.group("msg") or "").strip()
    return ParsedTrace(frames=frames, error_type=et, error_message=em,
                       language="go" if frames else "")


def _try_rust(log: str) -> ParsedTrace:
    file_matches = list(_RUST_FRAME_FILE.finditer(log))
    func_matches = list(_RUST_FRAME_NUM.finditer(log))
    frames = []
    for fm in file_matches:
        fp       = fm.group("file")
        line_num = int(fm.group("line"))
        file_pos = fm.start()
        best_func, best_pos = "<unknown>", -1
        for func_m in func_matches:
            if func_m.start() < file_pos and func_m.start() > best_pos:
                best_pos  = func_m.start()
                best_func = func_m.group("func").strip()
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1],
            line_number=line_num, function=best_func,
            language="rust", raw_line=fm.group(0),
        ))
    et, em = "panic", ""
    e = _RUST_ERROR.search(log)
    if e:
        em = (e.group("msg") or "").strip()
    return ParsedTrace(frames=frames, error_type=et, error_message=em,
                       language="rust" if frames else "")


def _try_c(log: str) -> ParsedTrace:
    frames = []
    for m in _C_FRAME.finditer(log):
        fp = m.group("file")
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1],
            line_number=int(m.group("line")), function=m.group("func"),
            language="c", raw_line=m.group(0),
        ))
    et = ""
    e = _C_ERROR.search(log)
    if e:
        et = e.group(0).strip()
    return ParsedTrace(frames=frames, error_type=et, error_message="",
                       language="c" if frames else "")


def _extract_generic_error_type(log: str) -> str:
    m = re.search(
        r'\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Panic|Fault))\b', log
    )
    return m.group(1) if m else ""


# ==========================================
# SYNTHESIZE VIRTUAL FRAME  (Case B)
# ==========================================

def _synthesize_frame_from_message(
    message: str, error_type: str
) -> StackFrame | None:
    """
    When there's no traceback (single-line error), try to
    extract the attribute/method name from the error message
    and create a virtual frame so the mapper has something
    to work with.

    Examples:
      "'NoneType' object has no attribute 'encode'"
        → function="encode"

      "object has no attribute 'find_user'"
        → function="find_user"

      "unsupported operand type(s) for +: 'int' and 'str'"
        → no synthesizable frame

      "cannot import name 'CartService' from 'cart_service'"
        → function="CartService"
    """
    if not message:
        return None

    # Pattern 1: "has no attribute 'method_name'"
    m = re.search(r"has no attribute ['\"]([^'\"]+)['\"]", message)
    if m:
        attr = m.group(1)
        return StackFrame(
            file_path   = "",
            file_name   = "",
            line_number = None,
            function    = attr,
            language    = "unknown",
            raw_line    = message,
        )

    # Pattern 2: "cannot import name 'ClassName'"
    m = re.search(r"cannot import name ['\"]([^'\"]+)['\"]", message)
    if m:
        return StackFrame(
            file_path   = "",
            file_name   = "",
            line_number = None,
            function    = m.group(1),
            language    = "unknown",
            raw_line    = message,
        )

    # Pattern 3: "'TypeName' object is not callable"
    m = re.search(r"['\"]([^'\"]+)['\"] object is not callable", message)
    if m:
        return StackFrame(
            file_path   = "",
            file_name   = "",
            line_number = None,
            function    = m.group(1),
            language    = "unknown",
            raw_line    = message,
        )


    # Pattern 4: "X is not a function" (JavaScript TypeError)
    # "transformed.puhs is not a function" -> func="puhs"
    m4 = re.search(r"(\w+)\s+is not a function", message)
    if m4:
        return StackFrame(
            file_path="", file_name="", line_number=None,
            function=m4.group(1), language="javascript", raw_line=message,
        )

    # Pattern 5: "X is not defined" (JavaScript ReferenceError)
    m5 = re.search(r"(\w+) is not defined", message)
    if m5:
        return StackFrame(
            file_path="", file_name="", line_number=None,
            function=m5.group(1), language="javascript", raw_line=message,
        )

    return None


# ==========================================
# COMPILER ERROR PARSERS
# ==========================================

_GCC_PAT = re.compile(
    r"^(?P<file>[^\s:]+\.[a-zA-Z0-9]+):(?P<line>\d+):(?:\d+:)?\s*(?:error|fatal error):\s*(?P<msg>.+)$",
    re.MULTILINE
)
_MSVC_PAT = re.compile(
    r"^(?P<file>[^(]+)\((?P<line>\d+)\)\s*:\s*error\s+[A-Z]\d+:\s*(?P<msg>.+)$",
    re.MULTILINE
)


def _try_gcc_clang(log: str) -> ParsedTrace:
    frames = []
    error_type, error_message = "", ""
    for m in _GCC_PAT.finditer(log):
        fp, msg, line = m.group("file"), m.group("msg").strip(), int(m.group("line"))
        func = "<compiler_error>"
        mm = re.search(r"has no member named ['\"](\w+)['\"]", msg)
        if mm:
            func = mm.group(1)
        else:
            mm = re.search(r"'(\w+)' was not declared", msg)
            if mm:
                func = mm.group(1)
        if not error_message:
            error_message = msg
        if not error_type:
            error_type = (
                "CompileError_UnresolvedMember"   if "has no member"      in msg else
                "CompileError_UndeclaredIdentifier" if "was not declared"  in msg else
                "CompileError_UndefinedReference"   if "undefined reference" in msg else
                "CompileError"
            )
        ext  = fp.split(".")[-1].lower() if "." in fp else ""
        lang = "cpp" if ext in ("cpp", "cc", "cxx", "hpp") else "c"
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=line, function=func, language=lang, raw_line=m.group(0),
        ))
    return ParsedTrace(frames=frames, error_type=error_type,
                       error_message=error_message, language="cpp" if frames else "")


def _try_msvc(log: str) -> ParsedTrace:
    frames = []
    error_type, error_message = "", ""
    for m in _MSVC_PAT.finditer(log):
        fp, msg, line = m.group("file").strip(), m.group("msg").strip(), int(m.group("line"))
        func = "<compiler_error>"
        mm = re.search(r"'(\w+)':\s*is not a member", msg)
        if mm:
            func = mm.group(1)
        if not error_message:
            error_message = msg
        if not error_type:
            error_type = "CompileError_MSVC"
        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=line, function=func, language="cpp", raw_line=m.group(0),
        ))
    return ParsedTrace(frames=frames, error_type=error_type,
                       error_message=error_message, language="cpp" if frames else "")


# ==========================================
# GO COMPILER ERROR PARSER
# e.g.: ./main.go:15:13: workers.ad undefined
#       (type []int has no field or method ad)
# ==========================================
_GO_COMPILER_PAT = re.compile(
    r"^(?P<file>[^\s:]+\.go):(?P<line>\d+):(?:\d+:)?\s*(?P<msg>.+)$",
    re.MULTILINE
)

def _try_go_compiler(log: str) -> ParsedTrace:
    frames = []
    error_type, error_message = "", ""

    for m in _GO_COMPILER_PAT.finditer(log):
        fp  = m.group("file")
        msg = m.group("msg").strip()
        line = int(m.group("line"))

        # Skip if this looks like a valid go line (not an error)
        if not any(kw in msg for kw in (
            "undefined","has no field","cannot","not found",
            "unknown","invalid","declared but not used","cannot use",
            "no method","cannot find"
        )):
            continue

        func = "<compiler_error>"
        # "workers.ad undefined" → func = "ad"
        undef_m = re.search(r"\w+\.(\w+)\s+undefined", msg)
        if undef_m:
            func = undef_m.group(1)
        else:
            # "type X has no field or method Y"
            field_m = re.search(r"has no field or method (\w+)", msg)
            if field_m:
                func = field_m.group(1)

        if not error_message:
            error_message = msg
        if not error_type:
            if "undefined" in msg:
                error_type = "CompileError_Undefined"
            elif "has no field" in msg or "no method" in msg:
                error_type = "CompileError_UnresolvedMember"
            else:
                error_type = "CompileError_Go"

        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=line, function=func, language="go", raw_line=m.group(0),
        ))

    return ParsedTrace(frames=frames, error_type=error_type,
                       error_message=error_message, language="go" if frames else "")


# ==========================================
# RUST COMPILER ERROR PARSER
# e.g.: error[E0599]: no method named `ad` found
#       for struct `Vec<{integer}>`
# ==========================================
_RUST_COMPILER_PAT = re.compile(
    r"^error(?:\[E\d+\])?\s*:\s*(?P<msg>.+)$",
    re.MULTILINE
)

def _try_rust_compiler(log: str) -> ParsedTrace:
    frames = []
    error_type, error_message = "", ""

    for m in _RUST_COMPILER_PAT.finditer(log):
        msg = m.group("msg").strip()

        func = "<compiler_error>"
        # "no method named `ad` found"
        method_m = re.search(r"no method named `(\w+)`", msg)
        if method_m:
            func = method_m.group(1)
            if not error_type:
                error_type = "CompileError_UnresolvedMethod"
        else:
            # "cannot find value `x` in this scope"
            val_m = re.search(r"cannot find (?:value|function|type) `(\w+)`", msg)
            if val_m:
                func = val_m.group(1)
                if not error_type:
                    error_type = "CompileError_Undefined"

        if not func or func == "<compiler_error>":
            continue

        if not error_message:
            error_message = msg

        # Try to find file/line from "  --> src/main.rs:9:5" following the error
        file_pat = re.search(r"-->\s+(?P<file>[^\s:]+\.rs):(?P<line>\d+)", log)
        fp   = file_pat.group("file") if file_pat else ""
        line = int(file_pat.group("line")) if file_pat else None

        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1] if fp else "",
            line_number=line, function=func, language="rust", raw_line=m.group(0),
        ))

    return ParsedTrace(frames=frames[:1], error_type=error_type,
                       error_message=error_message, language="rust" if frames else "")


# ==========================================
# JAVA COMPILER ERROR PARSER
# e.g.: error: cannot find symbol
#       symbol:   method ad(String)
#       location: variable payments of type ArrayList<String>
# ==========================================

def _try_java_compiler(log: str) -> ParsedTrace:
    if "cannot find symbol" not in log:
        return ParsedTrace()

    # Extract method name from "symbol: method X(...)"
    method_m = re.search(r"symbol:\s+method\s+(\w+)\s*\(", log)
    if not method_m:
        # "symbol: class X"
        class_m = re.search(r"symbol:\s+class\s+(\w+)", log)
        if class_m:
            func = class_m.group(1)
            error_type = "CompileError_UnresolvedClass"
        else:
            return ParsedTrace()
    else:
        func = method_m.group(1)
        error_type = "CompileError_UnresolvedMethod"

    # Try to get file/line from standard javac output
    # "FileName.java:42: error: cannot find symbol"
    file_m = re.search(r"(\w+\.java):(\d+):", log)
    fp   = file_m.group(1) if file_m else ""
    line = int(file_m.group(2)) if file_m else None

    # Extract location type
    loc_m = re.search(r"location:\s+(?:variable \w+ of type|class)\s+(\S+)", log)
    error_message = (
        f"Cannot find method '{func}' on {loc_m.group(1)}"
        if loc_m else f"Cannot find symbol: method {func}"
    )

    frame = StackFrame(
        file_path=fp, file_name=fp,
        line_number=line, function=func,
        language="java", raw_line=method_m.group(0),
    )
    return ParsedTrace(frames=[frame], error_type=error_type,
                       error_message=error_message, language="java")


# ==========================================
# C# ERROR PARSER
# e.g.: 'List<int>' does not contain a definition for 'Ad'
#       CS0117: 'X' does not contain a definition for 'Y'
# ==========================================
_CSHARP_PAT1 = re.compile(
    r"'[^']+' does not contain a definition for '(?P<method>\w+)'",
    re.IGNORECASE
)
_CSHARP_PAT2 = re.compile(
    r"CS\d+[:\s]+(?P<msg>.+)",
    re.IGNORECASE
)
# file.cs(line,col): error CS0XXX: message
_CSHARP_FILE = re.compile(
    r"^(?P<file>[^(]+)\((?P<line>\d+),(?:\d+)\):\s*error\s+CS\d+:\s*(?P<msg>.+)$",
    re.MULTILINE
)

def _try_csharp(log: str) -> ParsedTrace:
    frames = []
    error_type, error_message = "", ""

    # Try file-based error first
    for m in _CSHARP_FILE.finditer(log):
        fp   = m.group("file").strip()
        msg  = m.group("msg").strip()
        line = int(m.group("line"))

        func = "<compiler_error>"
        def_m = re.search(r"does not contain a definition for '(\w+)'", msg)
        if def_m:
            func = def_m.group(1)
            if not error_type:
                error_type = "CompileError_UnresolvedMember"

        if not error_message:
            error_message = msg

        frames.append(StackFrame(
            file_path=fp, file_name=fp.split("/")[-1].split("\\")[-1],
            line_number=line, function=func, language="csharp", raw_line=m.group(0),
        ))

    if not frames:
        # No file/line — try message-only pattern
        m = _CSHARP_PAT1.search(log)
        if m:
            func         = m.group("method")
            error_type   = "CompileError_UnresolvedMember"
            error_message = f"Does not contain a definition for '{func}'"
            frames.append(StackFrame(
                file_path="", file_name="",
                line_number=None, function=func,
                language="csharp", raw_line=m.group(0),
            ))

    return ParsedTrace(frames=frames, error_type=error_type,
                       error_message=error_message, language="csharp" if frames else "")