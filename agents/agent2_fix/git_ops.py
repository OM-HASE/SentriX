import subprocess
import os
from .config import TARGET_REPO_PATH


def run_git_command(command: list[str]):
    subprocess.run(
        command,
        cwd=TARGET_REPO_PATH,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def create_branch(branch_name: str):
    run_git_command(["git", "checkout", "-b", branch_name])


def commit_changes(message: str):
    run_git_command(["git", "add", "."])
    run_git_command(["git", "commit", "-m", message])
