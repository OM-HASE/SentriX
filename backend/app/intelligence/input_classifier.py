def classify_input(
    source_code=None,
    error_log=None
):

    if source_code and error_log:

        return "code_and_logs"

    elif source_code:

        return "code_only"

    elif error_log:

        return "logs_only"

    return "unknown"