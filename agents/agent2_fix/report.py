def build_fix_report(plan: dict) -> dict:
    return {
        "incident_id": plan["incident_id"],
        "branch_name": f"fix/{plan['incident_id']}",
        "files_modified": plan["files_targeted"],
        "patch_summary": plan["summary"],
        "risk_level": plan["risk_level"],
        "requires_validation": True,
        "pull_request_url": "pending"
    }
