import json
from pathlib import Path

def load_schema(schema_path: str) -> dict:
    path = Path(schema_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
