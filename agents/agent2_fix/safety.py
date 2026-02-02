FIXABLE_ROOT_CAUSE_KEYWORDS = {
    "missing",
    "without validation",
    "null",
    "none",
    "out-of-bounds",
    "timeout",
    "exceeded",
    "invalid",
    "not found"
}


def is_fixable(rca: dict) -> tuple[bool, str]:
    if rca["severity"] == "Critical":
        return False, "Critical severity is blocked"

    if rca["confidence"] not in {"Medium", "High"}:
        return False, "Insufficient RCA confidence"

    root = rca["root_cause"].lower()
    if not any(keyword in root for keyword in FIXABLE_ROOT_CAUSE_KEYWORDS):
        return False, "Root cause not eligible for deterministic fix"

    if not rca.get("affected_components"):
        return False, "No affected components"

    return True, "Eligible for fix"
