from fastapi import APIRouter
from pydantic import BaseModel
import git
import os

router = APIRouter()

REPO_DIR = "cloned_repos"

os.makedirs(REPO_DIR, exist_ok=True)

class RepoRequest(BaseModel):
    github_url: str

@router.post("/clone-repo")
def clone_repository(data: RepoRequest):

    repo_name = data.github_url.split("/")[-1].replace(".git", "")

    clone_path = os.path.join(REPO_DIR, repo_name)

    if os.path.exists(clone_path):
        return {
            "message": "Repository already exists",
            "path": clone_path
        }

    git.Repo.clone_from(data.github_url, clone_path)

    return {
        "message": "Repository cloned successfully",
        "repo_path": clone_path
    }