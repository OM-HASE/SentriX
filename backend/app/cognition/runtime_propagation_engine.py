import re


# =========================================
# BUILD PROPAGATION CHAIN
# =========================================

def build_runtime_propagation(

    error_log,

    source_code
):

    propagation_chain = []

    lower_error = error_log.lower()

    # =====================================
    # NULL POINTER
    # =====================================

    if "null" in lower_error:

        propagation_chain.extend([

            "Null Reference Access",

            "Service Execution Failure",

            "Runtime State Corruption",

            "Application Flow Interruption"
        ])

    # =====================================
    # DIVISION BY ZERO
    # =====================================

    if "zero" in lower_error:

        propagation_chain.extend([

            "Arithmetic Exception",

            "Computation Failure",

            "Execution Halt"
        ])

    # =====================================
    # INDEX OUT OF BOUNDS
    # =====================================

    if "index" in lower_error:

        propagation_chain.extend([

            "Invalid Memory Access",

            "Collection Boundary Failure",

            "Execution Flow Crash"
        ])

    # =====================================
    # INVALID METHOD
    # =====================================

    if "attributeerror" in lower_error \
    or "method" in lower_error:

        propagation_chain.extend([

            "Invalid Runtime API",

            "Method Resolution Failure",

            "Dependency Execution Halt"
        ])

    # =====================================
    # PARSE SOURCE CODE RISKS
    # =====================================

    if "runserver(" in source_code:

        propagation_chain.extend([

            "Flask Bootstrap Failure",

            "WSGI Initialization Failure",

            "Server Startup Collapse"
        ])

    return propagation_chain