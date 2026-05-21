import re

# ==========================================
# STACK TRACE PATTERNS
# ==========================================

STACKTRACE_PATTERNS = [

    # ======================================
    # JAVA
    # ======================================

    {
        "language": "java",

        "pattern":
        r'at\s+([a-zA-Z0-9_.$]+)\((.+?):(\d+)\)'
    },

    # ======================================
    # PYTHON
    # ======================================

    {
        "language": "python",

        "pattern":
        r'File\s+"(.+?)",\s+line\s+(\d+)'
    },

    # ======================================
    # JAVASCRIPT / NODE
    # ======================================

    {
        "language": "javascript",

        "pattern":
        r'at\s+.+?\s+\((.+?):(\d+):(\d+)\)'
    },

    # ======================================
    # GO
    # ======================================

    {
        "language": "go",

        "pattern":
        r'(.+?):(\d+)'
    }
]

# ==========================================
# EXCEPTION EXTRACTION
# ==========================================

def extract_exception_type(
    error_log
):

    patterns = [

        r'([a-zA-Z0-9_]+Exception)',

        r'([a-zA-Z0-9_]+Error)',

        r'panic:\s+(.+)',

        r'Traceback'
    ]

    for pattern in patterns:

        match = re.search(

            pattern,

            error_log
        )

        if match:

            return match.group(1)

    return "UnknownException"

# ==========================================
# PARSE STACK TRACE
# ==========================================

def parse_stacktrace(
    error_log
):

    stack_frames = []

    exception_type = (
        extract_exception_type(
            error_log
        )
    )

    # ======================================
    # PARSE FRAMES
    # ======================================

    for parser in STACKTRACE_PATTERNS:

        language = parser.get(
            "language"
        )

        pattern = parser.get(
            "pattern"
        )

        matches = re.finditer(

            pattern,

            error_log
        )

        for match in matches:

            # ==============================
            # JAVA
            # ==============================

            if language == "java":

                stack_frames.append({

                    "language":
                    language,

                    "exception_type":
                    exception_type,

                    "method":
                    match.group(1),

                    "file":
                    match.group(2),

                    "line":
                    int(match.group(3))
                })

            # ==============================
            # PYTHON
            # ==============================

            elif language == "python":

                stack_frames.append({

                    "language":
                    language,

                    "exception_type":
                    exception_type,

                    "file":
                    match.group(1),

                    "line":
                    int(match.group(2))
                })

            # ==============================
            # JAVASCRIPT
            # ==============================

            elif language == "javascript":

                stack_frames.append({

                    "language":
                    language,

                    "exception_type":
                    exception_type,

                    "file":
                    match.group(1),

                    "line":
                    int(match.group(2)),

                    "column":
                    int(match.group(3))
                })

            # ==============================
            # GO
            # ==============================

            elif language == "go":

                stack_frames.append({

                    "language":
                    language,

                    "exception_type":
                    exception_type,

                    "file":
                    match.group(1),

                    "line":
                    int(match.group(2))
                })

    return {

        "exception_type":
        exception_type,

        "stack_frames":
        stack_frames
    }