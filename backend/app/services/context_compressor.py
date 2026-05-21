def compress_context(
    context_documents,
    max_chars=2500
):

    combined = "\n\n".join(
        context_documents
    )

    if len(combined) > max_chars:

        combined = combined[
            :max_chars
        ]

    return combined