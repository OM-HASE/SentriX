from app.repository.repository_scanner import (
    scan_repository
)

from app.repository.repository_indexer import (
    RepositoryIndexer
)

from app.repository.cross_file_graph_builder import (
    CrossFileGraphBuilder
)

# ==========================================
# REPOSITORY PATH
# ==========================================

repository_path = (
    r"D:\SentriX\backend\cloned_repos\flask"
)

# ==========================================
# STEP 1: SCAN REPOSITORY
# ==========================================

print(
    "\n========== SCANNING REPOSITORY ==========\n"
)

repository_files = scan_repository(
    repository_path
)

print(
    f"FILES SCANNED: {len(repository_files)}"
)

# ==========================================
# STEP 2: BUILD REPOSITORY INDEX
# ==========================================

print(
    "\n========== BUILDING INDEX ==========\n"
)

indexer = RepositoryIndexer(
    repository_files
)

repository_index = (
    indexer.build_index()
)

print(
    f"INDEXED FILES: {len(repository_index)}"
)

# ==========================================
# STEP 3: BUILD CROSS-FILE GRAPH
# ==========================================

print(
    "\n========== BUILDING GRAPH ==========\n"
)

graph_builder = (
    CrossFileGraphBuilder(
        repository_index
    )
)

repository_graph = (
    graph_builder.build_graph()
)

# ==========================================
# STEP 4: GRAPH STATISTICS
# ==========================================

nodes = repository_graph.get(
    "nodes",
    []
)

edges = repository_graph.get(
    "edges",
    []
)

print(
    f"\nTOTAL NODES: {len(nodes)}"
)

print(
    f"TOTAL EDGES: {len(edges)}"
)

# ==========================================
# SAMPLE NODES
# ==========================================

print(
    "\n========== SAMPLE NODES ==========\n"
)

for node_id, node_data in list(nodes.items())[:10]:

    print({

        "id": node_id,

        **node_data
    })

# ==========================================
# SAMPLE EDGES
# ==========================================

print(
    "\n========== SAMPLE EDGES ==========\n"
)

for edge in list(edges)[:10]:

    print(edge)