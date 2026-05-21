from app.rag.retriever import (
    retrieve_relevant_chunks
)


def resolve_context(
    query
):

    retrieved = retrieve_relevant_chunks(
        query,
        top_k=2
    )

    context_documents = [

        item["document"]

        for item in retrieved
    ]

    return context_documents