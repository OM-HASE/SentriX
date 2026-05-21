from app.intelligence.tree_sitter_engine import (
    detect_language_tree_sitter,
    extract_functions_and_classes
)

python_code = """
class UserService:

    def login(self):
        print("login")

def hello():
    print("hello")
"""

language = detect_language_tree_sitter(
    python_code
)

print("\nDetected Language:")
print(language)

results = extract_functions_and_classes(
    python_code,
    language="python"
)

print("\nExtracted Structures:\n")

for item in results:

    print(item)
    print("\n-----------------\n")