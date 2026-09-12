# ============================================================
# firewall/store.py  — SQLite-backed fact store
# Upgraded from in-memory dict to persistent SQLite.
# ============================================================

import sqlite3
import hashlib
import time
import os
from typing import Optional

DB_PATH = os.environ.get("FIREWALL_DB", "firewall_facts.db")
_activity_log: list[dict] = []   # in-memory activity feed (last 200 events)

# ---------------------------------------------------------------------------
# DB init
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            statement     TEXT NOT NULL,
            files         TEXT NOT NULL,          -- JSON list of absolute paths
            content_hashes TEXT NOT NULL,         -- JSON {path: sha256}
            source_tool_call TEXT NOT NULL,
            raw_output    TEXT,
            created_at    REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_file(filepath: str) -> Optional[str]:
    """SHA-256 hash of a file's content. Returns None if file missing."""
    try:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def _row_to_dict(row: sqlite3.Row) -> dict:
    import json
    d = dict(row)
    d["files"] = json.loads(d["files"])
    d["content_hashes"] = json.loads(d["content_hashes"])
    return d


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def store_fact(
    statement: str,
    files: list[str],
    source_tool_call: str,
    raw_output: str,
) -> dict:
    import json
    content_hashes = {fp: hash_file(fp) for fp in files}
    now = time.time()

    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO facts (statement, files, content_hashes, source_tool_call, raw_output, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            statement,
            json.dumps(files),
            json.dumps(content_hashes),
            source_tool_call,
            raw_output,
            now,
        ),
    )
    fact_id = cursor.lastrowid
    conn.commit()
    conn.close()

    fact = {
        "id": fact_id,
        "statement": statement,
        "files": files,
        "content_hashes": content_hashes,
        "source_tool_call": source_tool_call,
        "raw_output": raw_output,
        "created_at": now,
    }
    _push_activity("stored", fact)
    return fact


def get_all_facts() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM facts ORDER BY id ASC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_fact(fact_id: int) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def clear_facts():
    """Delete all facts — used between demo runs."""
    conn = _get_conn()
    conn.execute("DELETE FROM facts")
    conn.commit()
    conn.close()
    _activity_log.clear()


# ---------------------------------------------------------------------------
# Activity log (in-memory, for dashboard feed)
# ---------------------------------------------------------------------------

def _push_activity(event_type: str, fact: Optional[dict], call_label: str = ""):
    _activity_log.append({
        "type": event_type,          # "avoided" | "executed" | "stored"
        "call": call_label or (fact["source_tool_call"] if fact else ""),
        "fact_id": fact["id"] if fact else None,
        "statement": fact["statement"] if fact else None,
        "ts": time.time(),
    })
    # Keep only last 200
    if len(_activity_log) > 200:
        _activity_log.pop(0)


def get_activity_log() -> list[dict]:
    return list(reversed(_activity_log))  # newest first


def push_avoided(call_label: str, fact: dict):
    _push_activity("avoided", fact, call_label)


def push_executed(call_label: str, fact: Optional[dict]):
    _push_activity("executed", fact, call_label)
