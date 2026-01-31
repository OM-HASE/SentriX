ERROR_KEYWORDS = [
    "error", "exception", "traceback", "failed", "crash", "bug"
]

def is_incident(payload: dict) -> bool:
    text = (
        payload.get("title", "") +
        payload.get("body", "") +
        payload.get("message", "")
    ).lower()

    return any(keyword in text for keyword in ERROR_KEYWORDS)