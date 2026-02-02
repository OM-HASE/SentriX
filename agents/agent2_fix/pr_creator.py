import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_API = "https://api.github.com"


def create_pull_request(branch_name: str, title: str, body: str) -> str:
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/pulls"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": "master"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in (200, 201):
        raise RuntimeError(f"PR creation failed: {response.text}")

    return response.json()["html_url"]
