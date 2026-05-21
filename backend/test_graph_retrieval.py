from app.graph.graph_builder import (
    build_repository_graph
)

from app.graph.graph_retriever import (
    retrieve_graph_neighbors
)

code = """
class AuthService:

    def login(self):

        validate_token()

def validate_token():

    return True
"""

build_repository_graph(code)

neighbors = retrieve_graph_neighbors(
    "login"
)

print(neighbors)