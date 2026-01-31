import json
import os
from .config import RCA_OUTPUT_FILE

def store_rca(rca: dict):
    # Ensure directory exists
    os.makedirs(os.path.dirname(RCA_OUTPUT_FILE), exist_ok=True)

    with open(RCA_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rca) + "\n")
