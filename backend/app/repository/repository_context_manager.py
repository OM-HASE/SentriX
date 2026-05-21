# ==========================================
# REPOSITORY CONTEXT MEMORY
# ==========================================

repository_context_memory = {

    "active_repository": None,

    "repository_graph": None,

    "repository_index": None,

    "repository_metadata": {}
}

# ==========================================
# STORE REPOSITORY CONTEXT
# ==========================================

def store_repository_context(

    repository_name,

    repository_graph,

    repository_index
):

    repository_context_memory[

        "active_repository"

    ] = repository_name

    repository_context_memory[

        "repository_graph"

    ] = repository_graph

    repository_context_memory[

        "repository_index"

    ] = repository_index

# ==========================================
# GET ACTIVE REPOSITORY GRAPH
# ==========================================

def get_repository_graph():

    return repository_context_memory.get(
        "repository_graph"
    )

# ==========================================
# GET REPOSITORY INDEX
# ==========================================

def get_repository_index():

    return repository_context_memory.get(
        "repository_index"
    )

# ==========================================
# GET ACTIVE REPOSITORY
# ==========================================

def get_active_repository():

    return repository_context_memory.get(
        "active_repository"
    )