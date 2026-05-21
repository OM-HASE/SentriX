# ==========================================
# BUILD SEMANTIC EDGES
# ==========================================

def build_semantic_edges(

    entities,

    relationships
):

    edges = []

    # ======================================
    # ENTITY LOOKUP
    # ======================================

    entity_names = set()

    for entity in entities:

        entity_name = entity.get(
            "entity_name"
        )

        if entity_name:

            entity_names.add(
                entity_name
            )

    # ======================================
    # RELATIONSHIP PROCESSING
    # ======================================

    for relation in relationships:

        relation_type = relation.get(
            "relationship_type"
        )

        # ==================================
        # FUNCTION CALL RELATIONSHIPS
        # ==================================

        if relation_type == "calls":

            object_name = relation.get(
                "object"
            )

            method_name = relation.get(
                "method"
            )

            signature = relation.get(
                "signature"
            )

            # ==============================
            # FALLBACK SIGNATURE
            # ==============================

            if not signature:

                if object_name and method_name:

                    signature = (
                        f"{object_name}.{method_name}"
                    )

            # ==============================
            # OBJECT -> SIGNATURE EDGE
            # ==============================

            if (

                object_name and
                signature and
                object_name != "global"

            ):

                edges.append({

                    "source":
                    object_name,

                    "target":
                    signature,

                    "relationship":
                    "calls"
                })

        # ==================================
        # IMPORT RELATIONSHIPS
        # ==================================

        elif relation_type == "imports":

            module_name = relation.get(
                "module"
            )

            if module_name:

                edges.append({

                    "source":
                    "repository",

                    "target":
                    module_name,

                    "relationship":
                    "imports"
                })

    return edges