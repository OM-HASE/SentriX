def extract_evidence(payload: dict) -> list[str]:
    evidence = []

    if "body" in payload and payload["body"]:
        evidence.append(payload["body"])

    if "message" in payload and payload["message"]:
        evidence.append(payload["message"])

    if "stacktrace" in payload:
        evidence.append(payload["stacktrace"])

    return evidence or ["No explicit evidence found"]