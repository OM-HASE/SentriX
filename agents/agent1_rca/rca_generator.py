import re
from datetime import datetime

def generate_incident_id() -> str:
    return f"INC-{int(datetime.utcnow().timestamp())}"

def generate_rca(payload: dict, evidence: list[str], incident_id: str | None = None) -> dict:
    text = " ".join(evidence).lower()

    if "keyerror" in text:
        root_cause = "Access to missing dictionary key without validation"
        fix = "Add key existence check before access"
        severity = "High"
    elif "indexerror" in text:
        root_cause = "Out-of-bounds index access"
        fix = "Validate index bounds before access"
        severity = "High"
    elif "timeout" in text:
        root_cause = "Operation exceeded configured timeout"
        fix = "Add retries or increase timeout threshold"
        severity = "Medium"
    else:
        root_cause = "Insufficient evidence for definitive root cause"
        fix = "Add additional logging for failure context"
        severity = "Low"

    affected = payload.get("files")
    if not affected:
        repo = payload.get("metadata", {}).get("repo", "unknown-repo")
        affected = [f"repo:{repo}"]

    return {
        "incident_id": incident_id or generate_incident_id(),
        "summary": payload.get("title", "Unhandled application failure"),
        "root_cause": root_cause,
        "trigger_event": payload.get("title", "Unknown trigger"),
        "impact": "Application functionality degraded or failed",
        "evidence": evidence,
        "affected_components": affected,
        "severity": severity,
        "recommended_fix": [fix],
        "preventive_actions": ["Improve validation and error handling"],
        "confidence": "Medium"
    }
