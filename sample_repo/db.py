# sample_repo/db.py
# A small database module — gives the agent a second file to investigate.

import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "app.db")


def get_connection() -> sqlite3.Connection:
    """Open and return a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return dicts instead of tuples
    return conn


def init_db():
    """Create the users table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt        TEXT NOT NULL,
            created_at  INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id: str) -> dict | None:
    """Fetch a user record by ID. Returns None if not found."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(user_id: str, email: str, password_hash: str, salt: str) -> bool:
    """Insert a new user. Returns True on success, False if email already exists."""
    import time
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, salt, created_at) VALUES (?,?,?,?,?)",
            (user_id, email, password_hash, salt, int(time.time())),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_user(user_id: str) -> bool:
    """Delete a user by ID. Returns True if a row was deleted."""
    conn = get_connection()
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
