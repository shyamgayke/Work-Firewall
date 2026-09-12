# ============================================================
# tools/real_tools.py — Real tool implementations
# ============================================================

import os
import re

SAMPLE_REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_repo"))


def grep_search(pattern: str, directory: str = None, path: str = None) -> str:
    """
    Search for a regex/string pattern inside .py files.
    Returns matching lines with filenames and line numbers.
    """
    search_dir = os.path.abspath(directory or path or SAMPLE_REPO_DIR)
    results = []

    for root, _, files in os.walk(search_dir):
        for fname in sorted(files):
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
    return "\n".join(results[:100])  # cap output


def read_file(filepath: str) -> str:
    """
    Read the contents of a file. Accepts absolute or relative-to-sample-repo paths.
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
    List all files in a directory (default: sample_repo).
    Returns relative paths for readability.
    """
    search_dir = os.path.abspath(directory or SAMPLE_REPO_DIR)
    base = search_dir  # relative to search_dir itself

    files = []
    for root, _, fnames in os.walk(search_dir):
        for fname in sorted(fnames):
            if fname.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(root, fname), base)
            files.append(rel)

    if not files:
        return "[list_files] No files found."
    return "\n".join(sorted(files))


# Registry — proxy.py looks up tool functions by name from here
TOOL_REGISTRY = {
    "grep_search": grep_search,
    "read_file":   read_file,
    "list_files":  list_files,
}
