import os

from app.intelligence.tree_sitter_engine import (
    detect_language
)

# ==========================================
# SUPPORTED SOURCE FILES
# ==========================================

SUPPORTED_EXTENSIONS = {

    ".py",
    ".java",
    ".js",
    ".ts",
    ".cpp",
    ".c",
    ".go",
    ".rs"
}

# ==========================================
# IGNORED DIRECTORIES
# ==========================================

IGNORED_DIRECTORIES = {

    "node_modules",

    "venv",

    ".git",

    "__pycache__",

    "dist",

    "build",

    "target"
}

# ==========================================
# VALID SOURCE FILE
# ==========================================

def is_supported_file(
    file_name
):

    _, extension = os.path.splitext(
        file_name
    )

    return extension in SUPPORTED_EXTENSIONS


# ==========================================
# SHOULD IGNORE DIRECTORY
# ==========================================

def should_ignore_directory(
    directory_name
):

    return directory_name in IGNORED_DIRECTORIES


# ==========================================
# READ SOURCE FILE
# ==========================================

def read_source_file(
    file_path
):

    try:

        with open(

            file_path,

            "r",

            encoding="utf-8"

        ) as file:

            return file.read()

    except Exception:

        return None


# ==========================================
# REPOSITORY SCAN
# ==========================================

def scan_repository(
    repository_path
):

    repository_files = []

    for root, dirs, files in os.walk(
        repository_path
    ):

        # ==================================
        # FILTER DIRECTORIES
        # ==================================

        dirs[:] = [

            directory

            for directory in dirs

            if not should_ignore_directory(
                directory
            )
        ]

        # ==================================
        # PROCESS FILES
        # ==================================

        for file_name in files:

            if not is_supported_file(
                file_name
            ):

                continue

            file_path = os.path.join(

                root,

                file_name
            )

            source_code = read_source_file(
                file_path
            )

            if not source_code:

                continue

            # ==============================
            # DETECT LANGUAGE
            # ==============================

            try:

                language = detect_language(
                    source_code
                )

            except Exception:

                language = "unknown"

            repository_files.append({

                "file_name":
                file_name,

                "file_path":
                file_path,

                "language":
                language,

                "source_code":
                source_code
            })

    return repository_files