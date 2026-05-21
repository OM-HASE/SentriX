from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional


from app.intelligence.workflow_router import (
    route_workflow
)

router = APIRouter()

class IntelligenceRequest(BaseModel):

    source_code: Optional[str] = None

    error_log: Optional[str] = None

@router.post("/analyze-input")

async def analyze_input(
    data: IntelligenceRequest
):

    result = route_workflow(

        source_code=data.source_code,

        error_log=data.error_log
    )

    return result