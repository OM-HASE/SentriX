from app.services.universal_chunker import (
    universal_chunk_code
)

python_code = """
class UserService:

    def login(self):
        print("login")

def hello():
    print("hello")
"""

chunks = universal_chunk_code(
    python_code
)

for chunk in chunks:

    print("\n==================\n")

    print(chunk)