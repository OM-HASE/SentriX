# ==========================================
# METHOD KNOWLEDGE ENGINE
# ==========================================

class MethodKnowledgeEngine:

    def __init__(self):

        # ==================================
        # MINIMAL SEMANTIC KNOWLEDGE
        # ==================================

        self.known_methods = {

            "ArrayList": [

                "add",
                "remove",
                "clear",
                "size",
                "get"
            ],

            "System.out": [

                "println",
                "print"
            ]
        }

    # ======================================
    # METHOD VALIDATION
    # ======================================

    def validate_method(

        self,

        object_type,

        method_name
    ):

        methods = self.known_methods.get(
            object_type,
            []
        )

        return method_name in methods