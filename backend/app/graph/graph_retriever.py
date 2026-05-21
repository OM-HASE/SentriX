from app.graph.graph_memory import (
    repository_graph_memory
)


def retrieve_graph_neighbors(
    entity_name
):

    graph = repository_graph_memory.get(
        "active_graph"
    )

    if not graph:

        return []

    edges = graph["edges"]

    neighbors = []

    for edge in edges:

        if edge["source"] == entity_name:

            neighbors.append({

                "target":
                edge["target"],

                "relationship":
                edge["relationship"]
            })

        elif edge["target"] == entity_name:

            neighbors.append({

                "source":
                edge["source"],

                "relationship":
                edge["relationship"]
            })

    return neighbors