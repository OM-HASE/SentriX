from app.repository.repository_scanner import (
    scan_repository
)

from app.repository.repository_indexer import (
    RepositoryIndexer
)

from app.graph.graph_builder import (
    build_repository_graph
)
from app.graph.graph_memory import (
    repository_graph_memory
)

# ==========================================
# SCAN TEST REPOSITORY
# ==========================================

files = scan_repository(
    r"D:\SentriX\backend\test_repo_cross_file"
)

# ==========================================
# INDEX REPOSITORY
# ==========================================

indexer = RepositoryIndexer(
    files
)

repository_index = (
    indexer.build_index()
)
repository_graph_memory[
    "repository_index"
] = repository_index

# ==========================================
# BUILD GRAPH
# ==========================================

for file in repository_index:

    build_repository_graph(
        file.get(
            "source_code",
            ""
        )
    )

print("\n========== REPOSITORY BUILT ==========\n")

print(
    len(repository_index)
)