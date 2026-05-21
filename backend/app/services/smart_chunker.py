import ast


def chunk_python_code(content):

    chunks = []

    try:

        tree = ast.parse(content)

        for node in ast.walk(tree):

            if isinstance(node, (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef
            )):

                start_line = node.lineno

                end_line = getattr(
                    node,
                    "end_lineno",
                    start_line
                )

                lines = content.splitlines()

                snippet = "\n".join(
                    lines[start_line - 1:end_line]
                )

                chunks.append({
                    "type": type(node).__name__,
                    "name": node.name,
                    "start_line": start_line,
                    "end_line": end_line,
                    "content": snippet
                })

    except Exception:

        return []

    return chunks

def fallback_chunking(
    content,
    chunk_size=1200
):

    chunks = []

    for i in range(0, len(content), chunk_size):

        chunk = content[i:i + chunk_size]

        chunks.append({
            "type": "generic",
            "name": f"chunk_{i}",
            "content": chunk
        })

    return chunks

def smart_chunk_code(
    content,
    language
):

    if language == "Python":

        chunks = chunk_python_code(
            content
        )

        if chunks:
            return chunks

    return fallback_chunking(content)