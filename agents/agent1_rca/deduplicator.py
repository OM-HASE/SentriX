import hashlib

# In-memory store (V1)
INCIDENT_SIGNATURES = {}

def generate_signature(root_cause: str, affected_components: list[str]) -> str:
    signature_source = root_cause + "|" + "|".join(sorted(affected_components))
    return hashlib.sha256(signature_source.encode()).hexdigest()


def check_duplicate(signature: str) -> str | None:
    """
    Returns existing incident_id if duplicate exists
    """
    return INCIDENT_SIGNATURES.get(signature)


def register_incident(signature: str, incident_id: str):
    INCIDENT_SIGNATURES[signature] = incident_id
