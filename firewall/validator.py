# ============================================================
# firewall/validator.py  — Person B's file
#
# HOUR 0-1: Stub (always returns valid) — proxy.py uses
#           store.py's hash_file directly for now.
# HOUR 1-4: Person B implements proper file-hash validation here.
# ============================================================

import os
from firewall.store import hash_file


def is_fact_valid(fact: dict) -> bool:
    """
    Check if a stored fact is still valid by verifying the files it
    depends on haven't changed (whole-file SHA-256 hash comparison).

    Returns:
        True  — fact is still valid, safe to reuse
        False — one or more files changed; fact is stale, must re-run tool
    """
    for filepath, stored_hash in fact.get("content_hashes", {}).items():
        current_hash = hash_file(filepath)
        if current_hash is None:
            # File was deleted — definitely stale
            return False
        if current_hash != stored_hash:
            # File changed since fact was extracted — stale
            return False
    return True

# TODO (Person B, Hour 1-4):
# - Move storage from dict → SQLite here or in store.py
# - Add line-range hashing as a stretch goal (not required for MVP)
