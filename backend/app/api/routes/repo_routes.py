from fastapi import APIRouter
from pydantic import BaseModel

from app.services.repo_processor import (
    scan_repository,
    store_chunks_in_vector_db
)

router = APIRouter()

class RepoPathRequest(BaseModel):
    repo_path: str

@router.post("/process-repo")
def process_repository(data: RepoPathRequest):

    result = scan_repository(data.repo_path)

    store_chunks_in_vector_db(
        result["chunks"]
    )

    return {
        "message": "Repository processed successfully",
        "total_chunks": len(result["chunks"]),
        "languages": result["languages"]
    }