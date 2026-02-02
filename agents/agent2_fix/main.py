from .config import RCA_NDJSON_PATH
from .rca_reader import read_all_rcas
from .safety import is_fixable
from .fix_engine import generate_fix_plan
from .report import build_fix_report
from .git_ops import create_branch, commit_changes
from .pr_creator import create_pull_request

def run():
    rcas = read_all_rcas(RCA_NDJSON_PATH)

    results = []
    processed_incidents = set()

    for rca in rcas:
        incident_id = rca["incident_id"]

        if incident_id in processed_incidents:
            continue

        processed_incidents.add(incident_id)

        allowed, reason = is_fixable(rca)
        if not allowed:
            results.append({
                "incident_id": incident_id,
                "status": "skipped",
                "reason": reason
            })
            continue

        plan = generate_fix_plan(rca)
        if not plan["files_targeted"]:
            results.append({
                "incident_id": incident_id,
                "status": "skipped",
                "reason": "No safe KeyError patterns found in files"
            })
            continue

        branch_name = f"fix/{incident_id}"
        create_branch(branch_name)
        commit_message = f"fix({incident_id}): {plan['summary']}"
        commit_changes(commit_message) 
        report = build_fix_report(plan)
        report["branch_name"] = branch_name
        results.append({
            "incident_id": rca["incident_id"],
            "status": "planned",
            "report": report
        })

    return results


if __name__ == "__main__":
    output = run()
    for item in output:
        print(item)
