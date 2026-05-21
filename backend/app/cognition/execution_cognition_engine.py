def build_execution_cognition(

    error_log,

    source_code,

    graph_data
):

    execution_flow = []

    runtime_breakpoints = []

    propagation_chain = []

    state_failures = []

    # ====================================
    # ATTRIBUTE ERROR DETECTION
    # ====================================

    if "AttributeError" in error_log:

        execution_flow.append({

            "stage":
            "runtime_method_resolution",

            "status":
            "failed",

            "reason":
            "invalid object attribute access"
        })

        runtime_breakpoints.append({

            "breakpoint":
            "method_lookup_failure",

            "location":
            error_log
        })


    # ====================================
    # GRAPH-AWARE EXECUTION ANALYSIS
    # ====================================

    if graph_data:

        for edge in graph_data.get(
            "edges",
            []
        ):

            execution_flow.append({

                "source":
                edge["source"],

                "target":
                edge["target"],

                "relationship":
                edge["relationship"]
            })

    return {

        "execution_flow":
        execution_flow,

        "runtime_breakpoints":
        runtime_breakpoints,

        "propagation_chain":
        propagation_chain,

        "state_failures":
        state_failures
    }