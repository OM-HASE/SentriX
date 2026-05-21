from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.retriever import (
    retrieve_relevant_chunks
)

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/retrieve")

def retrieve_context(data: QueryRequest):

    results = retrieve_relevant_chunks(
        data.query
    )

    return results