from fastapi import FastAPI, Request, HTTPException
from .detector import is_incident
from .evidence import extract_evidence
from .rca_generator import generate_rca
from .storage import store_rca
from .deduplicator import (generate_signature, check_duplicate, register_incident)
from common.utils.schema_validator import validate_schema
from common.utils.load_schema import load_schema
from common.github.parser import parse_github_event

app = FastAPI(title="SentriX Agent-1")
RCA_SCHEMA = load_schema("common/schemas/rca.schema.json")

@app.post("/webhook/github")
async def github_webhook(request: Request):
    raw_payload = await request.json()
    headers = dict(request.headers)
    try:
        payload = parse_github_event(headers, raw_payload)
    except Exception: 
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not is_incident(payload):
        return {"status": "ignored", "reason": "not an incident"}

    evidence = extract_evidence(payload)
    temp_rca = generate_rca(payload, evidence)
    signature = generate_signature(
        temp_rca["root_cause"],
        temp_rca["affected_components"]
    )

    existing_incident_id = check_duplicate(signature)

    if existing_incident_id:
        rca = generate_rca(payload, evidence, incident_id=existing_incident_id)
    else:
        rca = temp_rca
        register_incident(signature, rca["incident_id"])
    
    try:
        validate_schema(rca, RCA_SCHEMA)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))    

    store_rca(rca)

    return {
        "status": "rca_created",
        "incident_id": rca["incident_id"]
    }


@app.get("/health")
def health():
    return {"status": "ok"}
