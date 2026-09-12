# ============================================================
# tools/real_tools.py  — Person A's file
# Stub placeholders so proxy.py can import them NOW.
# Person A will replace these with real implementations.
# ============================================================

import os
import re

SAMPLE_REPO_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_repo")


def grep_search(pattern: str, path: str = None) -> str:
    """
    Search for a regex/string pattern inside files in sample_repo.
    Returns matching lines with filenames and line numbers.
    Person A: replace stub logic here with your real implementation.
    """
    search_dir = os.path.abspath(path or SAMPLE_REPO_DIR)
    results = []

    for root, _, files in os.walk(search_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append(f"{fname}:{i}: {line.rstrip()}")
            except Exception:
                pass

    if not results:
        return f"[grep_search] No matches found for pattern: '{pattern}'"
    return "\n".join(results)


def read_file(filepath: str) -> str:
    """
    Read the contents of a file inside sample_repo.
    Person A: adjust path handling / safety checks as needed.
    """
    abs_path = os.path.abspath(
        os.path.join(SAMPLE_REPO_DIR, filepath)
        if not os.path.isabs(filepath)
        else filepath
    )
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"[read_file] File not found: {filepath}"
    except Exception as e:
        return f"[read_file] Error: {e}"


def list_files(directory: str = None) -> str:
    """
    List Python files in the sample_repo (or a subdirectory of it).
    """
    search_dir = os.path.abspath(
        os.path.join(SAMPLE_REPO_DIR, directory) if directory else SAMPLE_REPO_DIR
    )
    files = []
    for root, _, fnames in os.walk(search_dir):
        for fname in fnames:
            rel = os.path.relpath(os.path.join(root, fname), SAMPLE_REPO_DIR)
            files.append(rel)
    if not files:
        return "[list_files] No files found."
    return "\n".join(sorted(files))


# Registry — proxy.py looks up tool functions by name from here
TOOL_REGISTRY = {
    "grep_search": grep_search,
    "read_file": read_file,
    "list_files": list_files,
}
