import os
import re
from .config import TARGET_REPO_PATH

def apply_keyerror_fix(file_path: str) -> bool:
    if not file_path.endswith(".py"):
        return False

    full_path = os.path.join(TARGET_REPO_PATH, file_path)

    if not os.path.exists(full_path):
        return False

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 🔒 IDMPOTENCY CHECK: guard already exists
    guard_pattern = r'if\s+"user_id"\s+not\s+in\s+data'
    if re.search(guard_pattern, content):
        return False  # already fixed

    lines = content.splitlines(keepends=True)
    new_lines = []
    modified = False

    for line in lines:
        match = re.search(r'(\w+)\s*=\s*(\w+)\["(\w+)"\]', line)

        if match:
            _, dict_name, key = match.groups()

            guard = (
                f'    if "{key}" not in {dict_name}:\n'
                f'        raise ValueError("Missing {key} in {dict_name}")\n'
            )

            new_lines.append(guard)
            new_lines.append(line)
            modified = True
        else:
            new_lines.append(line)

    if modified:
        with open(full_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return modified


def generate_fix_plan(rca: dict) -> dict:
    modified_files = []

    for file_path in rca["affected_components"]:
        if file_path.startswith("repo:"):
            continue

        success = apply_keyerror_fix(file_path)
        if success:
            modified_files.append(file_path)

    return {
        "incident_id": rca["incident_id"],
        "strategy": "keyerror_guard_fix",
        "summary": rca["recommended_fix"][0],
        "files_targeted": modified_files,
        "risk_level": "Low"
    }
