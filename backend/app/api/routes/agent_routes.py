from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.rca_agent import (
    analyze_root_cause
)

router = APIRouter()

class RCARequest(BaseModel):
    error_log: str
    source_code: str

@router.post("/analyze-error")

async def analyze_error(data: RCARequest):

    result = analyze_root_cause(
        error_log=data.error_log,
        source_code=data.source_code
    )

    return {
        "analysis": result
    }