from app.graph.graph_builder import (
    build_repository_graph
)

from app.agents.graph_rca_agent import (
    analyze_graph_root_cause
)

code = """
import flask

class AuthService:

    def login(self):

        validate_token()

        print("login")

def validate_token():

    return True

app.runserver(debug=True)
"""

# Build graph first
build_repository_graph(code)

result = analyze_graph_root_cause(

    error_log=
    "AttributeError: Flask object has no attribute runserver",

    source_code=code
)

print(result)