import json

def read_all_rcas(path: str) -> list[dict]:
    rcas = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rcas.append(json.loads(line))
    except FileNotFoundError:
        pass
    return rcas
