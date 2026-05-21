from app.intelligence.input_classifier import (
    classify_input
)

from app.intelligence.language_detector import (
    detect_language
)

from app.intelligence.log_parser import (
    parse_error_log
)

from app.intelligence.context_resolver import (
    resolve_context
)


def route_workflow(
    source_code=None,
    error_log=None
):

    workflow = classify_input(
        source_code,
        error_log
    )

    result = {
        "workflow_type": workflow
    }

    # CODE ONLY
    if workflow == "code_only":

        language = detect_language(
            source_code
        )

        result["language"] = language

        result["mode"] = (
            "static_analysis"
        )

    # CODE + LOGS
    elif workflow == "code_and_logs":

        language = detect_language(
            source_code
        )

        parsed_logs = parse_error_log(
            error_log
        )

        context = resolve_context(
            error_log + "\n" + source_code
        )

        result["language"] = language

        result["parsed_errors"] = (
            parsed_logs
        )

        result["retrieved_context"] = (
            context
        )

        result["mode"] = (
            "runtime_rca"
        )

    # LOGS ONLY
    elif workflow == "logs_only":

        parsed_logs = parse_error_log(
            error_log
        )

        context = resolve_context(
            error_log
        )

        result["parsed_errors"] = (
            parsed_logs
        )

        result["retrieved_context"] = (
            context
        )

        result["mode"] = (
            "repository_rca"
        )

    return result