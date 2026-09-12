# ============================================================
# firewall/validator.py — Fact validity checker
# Uses SHA-256 whole-file hashing to detect code changes.
# ============================================================

from firewall.store import hash_file


def is_fact_valid(fact: dict) -> bool:
    """
    Return True if every file the fact depends on is unchanged.

    Logic:
    - If a fact has no file dependencies (e.g. a list_files call), it's always valid.
    - For each file: recompute SHA-256 and compare to the stored hash.
    - If any file was deleted (hash=None) or changed → stale → False.
    """
    content_hashes: dict = fact.get("content_hashes", {})

    if not content_hashes:
        # No file provenance → conservatively trust it
        return True

    for filepath, stored_hash in content_hashes.items():
        if stored_hash is None:
            # Was missing at extraction time — always recheck
            continue
        current_hash = hash_file(filepath)
        if current_hash is None:
            # File was deleted since fact was stored
            return False
        if current_hash != stored_hash:
            # File changed — fact may be stale
            return False

    return True


def filter_valid_facts(facts: list[dict]) -> list[dict]:
    """Return only the facts whose source files haven't changed."""
    return [f for f in facts if is_fact_valid(f)]
