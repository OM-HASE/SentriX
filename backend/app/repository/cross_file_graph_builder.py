from app.graph.knowledge_graph import (
    RepositoryKnowledgeGraph
)

from app.graph.semantic_edge_engine import (
    build_semantic_edges
)

# ==========================================
# CROSS FILE GRAPH BUILDER
# ==========================================

class CrossFileGraphBuilder:

    def __init__(

        self,

        repository_index
    ):

        self.repository_index = (
            repository_index
        )

        self.graph = (
            RepositoryKnowledgeGraph()
        )

    # ======================================
    # BUILD REPOSITORY GRAPH
    # ======================================

    def build_graph(
        self
    ):

        all_entities = []

        all_relationships = []

        # ==================================
        # PROCESS FILES
        # ==================================

        for file_data in self.repository_index:

            entities = file_data.get(
                "entities",
                []
            )

            relationships = file_data.get(
                "relationships",
                []
            )

            file_path = file_data.get(
                "file_path"
            )

            # ==============================
            # ENTITY NODES
            # ==============================

            for entity in entities:

                entity_name = entity.get(
                    "entity_name"
                )

                entity_type = entity.get(
                    "entity_type"
                )

                self.graph.add_node(

                    node_id=entity_name,

                    node_type=entity_type,

                    metadata={

                        "file_path":
                        file_path,

                        **entity
                    }
                )

                all_entities.append(
                    entity
                )

            # ==============================
            # RELATIONSHIP NODES
            # ==============================

            for relation in relationships:

                relation_type = relation.get(
                    "relationship_type"
                )

                if relation_type == "calls":

                    relation_node = relation.get(
                        "signature"
                    )

                elif relation_type == "imports":

                    relation_node = relation.get(
                        "module"
                    )

                else:

                    relation_node = str(
                        relation
                    )

                self.graph.add_node(

                    node_id=relation_node,

                    node_type=relation_type,

                    metadata={

                        "file_path":
                        file_path,

                        **relation
                    }
                )

                all_relationships.append(
                    relation
                )

        # ==================================
        # BUILD SEMANTIC EDGES
        # ==================================

        semantic_edges = (
            build_semantic_edges(

                all_entities,

                all_relationships
            )
        )

        # ==================================
        # ADD GRAPH EDGES
        # ==================================

        for edge in semantic_edges:

            self.graph.add_edge(

                source=edge["source"],

                target=edge["target"],

                relationship=edge[
                    "relationship"
                ]
            )

        return self.graph.get_graph()