import os
from pathlib import Path
from app.rag.embeddings import embedding_model
from app.rag.vector_store import collection
from app.services.universal_chunker import universal_chunk_code
from app.core.cache import embedding_cache 

SUPPORTED_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React",
    ".tsx": "React",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".md": "Markdown"
}

IGNORE_DIRS = {
    "node_modules",
    "venv",
    ".git",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".idea",
    ".vscode"
}

def scan_repository(repo_path):

    repository_data = {
        "repo_name": os.path.basename(repo_path),
        "languages": set(),
        "files": [],
        "chunks": []
    }

    for root, dirs, files in os.walk(repo_path):

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:

            file_path = os.path.join(root, file)

            extension = Path(file).suffix

            if extension not in SUPPORTED_EXTENSIONS:
                continue

            language = SUPPORTED_EXTENSIONS[extension]

            repository_data["languages"].add(language)

            relative_path = os.path.relpath(file_path, repo_path)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

            except Exception:
                continue

            repository_data["files"].append({
                "path": relative_path,
                "language": language,
                "size": len(content)
            })

            chunks = universal_chunk_code(content)

            for idx, chunk in enumerate(chunks):

                repository_data["chunks"].append({
                    "file": relative_path,
                    "chunk_id": idx + 1,
                    "language": language,
                    "type": chunk.get("type"),
                    "name": chunk.get("name"),
                    "start_line": chunk.get("start_line"),
                    "end_line": chunk.get("end_line"),
                    "content": chunk["content"]
                })

    repository_data["languages"] = list(repository_data["languages"])

    return repository_data

def create_chunks(content, chunk_size=1000):

    chunks = []

    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        chunks.append(chunk)

    return chunks

def store_chunks_in_vector_db(chunks):

    for chunk in chunks:

        cache_key = chunk["content"]

        # Check cache first
        if cache_key in embedding_cache:

            embedding = embedding_cache[
                cache_key
            ]

        else:

            embedding = embedding_model.encode(
                chunk["content"]
            ).tolist()

            embedding_cache[
                cache_key
            ] = embedding

        collection.add(

            ids=[
                f"{chunk['file']}_{chunk['chunk_id']}"
            ],

            embeddings=[embedding],

            documents=[
                chunk["content"]
            ],

            metadatas=[{

    "file": str(chunk["file"]),

    "language": str(chunk["language"]),

    "type": str(
        chunk.get("type", "")
    ),

    "name": str(
        chunk.get("name", "")
    ),

    "start_line": int(
        chunk.get("start_line", 0) or 0
    ),

    "end_line": int(
        chunk.get("end_line", 0) or 0
    )
}]
        )