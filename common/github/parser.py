def parse_github_event(headers: dict, payload: dict) -> dict:
    """
    Normalize different GitHub events into a common structure
    """

    event_type = headers.get("x-github-event", "unknown")

    if event_type == "issues":
        issue = payload.get("issue", {})

        return {
            "event_type": "issue",
            "title": issue.get("title", ""),
            "body": issue.get("body", ""),
            "files": [],
            "metadata": {
                "issue_number": issue.get("number"),
                "repo": payload.get("repository", {}).get("full_name")
            }
        }

    if event_type == "pull_request":
        pr = payload.get("pull_request", {})

        return {
            "event_type": "pull_request",
            "title": pr.get("title", ""),
            "body": pr.get("body", ""),
            "files": [],
            "metadata": {
                "pr_number": pr.get("number"),
                "repo": payload.get("repository", {}).get("full_name")
            }
        }

    if event_type == "workflow_run":
        workflow = payload.get("workflow_run", {})

        return {
            "event_type": "ci_failure",
            "title": workflow.get("name", ""),
            "body": workflow.get("conclusion", ""),
            "files": [],
            "metadata": {
                "run_id": workflow.get("id"),
                "repo": payload.get("repository", {}).get("full_name")
            }
        }

    return {
        "event_type": "unknown",
        "title": payload.get("title", ""),
        "body": payload.get("body", ""),
        "files": payload.get("files", []),
        "metadata": {}
    }
