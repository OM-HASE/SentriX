# ==========================================
# REPOSITORY CONTEXT EXPANSION ENGINE
# ==========================================

class RepositoryContextExpansionEngine:

    # ======================================
    # INITIALIZATION
    # ======================================

    def __init__(

        self,

        repository_index
    ):

        self.repository_index = (
            repository_index or []
        )

    # ======================================
    # EXPAND CONTEXT
    # ======================================

    def expand_context(

        self,

        source_code
    ):

        expanded_files = []

        import_targets = []

        lines = source_code.splitlines()

        # ==================================
        # IMPORT DISCOVERY
        # ==================================

        for line in lines:

            stripped = line.strip()

            # ==============================
            # PYTHON IMPORTS
            # ==============================

            if stripped.startswith(
                "from "
            ):

                parts = stripped.split()

                if len(parts) >= 2:

                    import_targets.append(
                        parts[1]
                    )

            elif stripped.startswith(
                "import "
            ):

                parts = stripped.split()

                if len(parts) >= 2:

                    import_targets.append(
                        parts[1]
                    )

        # ==================================
        # REPOSITORY MATCHING
        # ==================================

        for file_data in (

            self.repository_index
        ):

            file_name = file_data.get(
                "file_name",
                ""
            )

            module_name = (
                file_name
                .replace(".py", "")
                .replace(".java", "")
            )

            if module_name in import_targets:

                expanded_files.append(
                    file_data
                )

        return {

            "expanded_files":
            expanded_files,

            "import_targets":
            import_targets
        }