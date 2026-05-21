from app.graph.graph_builder import (
    build_repository_graph
)

code = """
import flask

class AuthService:

    def login(self):

        validate_token()

        print("login")

def validate_token():

    return True
"""

graph = build_repository_graph(
    code
)

print(graph)