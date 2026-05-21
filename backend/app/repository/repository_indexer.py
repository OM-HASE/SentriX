from app.graph.entity_extractor import (
    extract_code_entities
)

from app.graph.semantic_relationship_extractor import (
    extract_semantic_relationships
)

# ==========================================
# REPOSITORY INDEXER
# ==========================================

class RepositoryIndexer:

    def __init__(

        self,

        repository_files
    ):

        self.repository_files = (
            repository_files
        )

    # ======================================
    # BUILD INDEX
    # ======================================

    def build_index(
        self
    ):

        repository_index = []

        for file_data in self.repository_files:

            file_name = file_data.get(
                "file_name"
            )

            file_path = file_data.get(
                "file_path"
            )

            language = file_data.get(
                "language"
            )

            source_code = file_data.get(
                "source_code"
            )

            # ==============================
            # ENTITY EXTRACTION
            # ==============================

            try:

                entities = (
                    extract_code_entities(
                        source_code
                    )
                )

            except Exception:

                entities = []

            # ==============================
            # RELATIONSHIP EXTRACTION
            # ==============================

            try:

                relationships = (
                    extract_semantic_relationships(

                        source_code,

                        language=language
                    )
                )

            except Exception:

                relationships = []

            # ==============================
            # FILE INDEX ENTRY
            # ==============================

            repository_index.append({

                "file_name":
                file_name,

                "file_path":
                file_path,

                "language":
                language,

                "entities":
                entities,

                "relationships":
                relationships
            })

        return repository_index