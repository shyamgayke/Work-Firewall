# ============================================================
# firewall/store.py  — Person B's file
# Hour 0-1: plain Python dict store (no SQLite yet).
# Person B will migrate this to SQLite in Hour 1-4.
# ============================================================

import hashlib
import time
import os
from typing import Optional


# ---------------------------------------------------------------------------
# In-memory fact store (Hour 0-1 version — just a list of dicts)
# ---------------------------------------------------------------------------
_facts: list[dict] = []


def hash_file(filepath: str) -> Optional[str]:
    """SHA-256 hash of a file's content for invalidation checks."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def store_fact(
    statement: str,
    files: list[str],
    source_tool_call: str,
    raw_output: str,
) -> dict:
    """
    Create and store a new fact.
    `files` should be absolute paths so hashing is unambiguous.
    """
    content_hashes = {fp: hash_file(fp) for fp in files}

    fact = {
        "id": len(_facts) + 1,
        "statement": statement,
        "files": files,
        "content_hashes": content_hashes,  # {filepath: sha256}
        "source_tool_call": source_tool_call,
        "raw_output": raw_output,
        "created_at": time.time(),
    }
    _facts.append(fact)
    return fact


def get_all_facts() -> list[dict]:
    """Return all currently stored facts."""
    return list(_facts)


def clear_facts():
    """Clear the fact store (useful between test runs)."""
    _facts.clear()
