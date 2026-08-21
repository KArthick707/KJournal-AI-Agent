"""SQLite storage for journal entries. No ORM -- a personal journal is one
table with simple queries, so plain sqlite3 keeps this readable."""

import json
import sqlite3
import threading
from datetime import datetime, timezone

# The app shares one sqlite3.Connection across FastAPI's event loop thread
# (async routes) and its threadpool (sync routes). check_same_thread=False
# lifts sqlite3's same-thread restriction; this lock serializes access since
# lifting that restriction doesn't make the connection itself thread-safe.
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    summary TEXT,
    mood TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    audio_path TEXT,
    structured INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with _lock:
        conn.execute(SCHEMA)
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    d["structured"] = bool(d["structured"])
    return d


def create_entry(
    conn: sqlite3.Connection,
    *,
    source: str,
    raw_text: str,
    title: str,
    body: str,
    summary: str | None = None,
    mood: str | None = None,
    tags: list[str] | None = None,
    audio_path: str | None = None,
    structured: bool = False,
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        cur = conn.execute(
            """
            INSERT INTO entries
                (created_at, source, raw_text, title, body, summary, mood, tags, audio_path, structured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                source,
                raw_text,
                title,
                body,
                summary,
                mood,
                json.dumps(tags or []),
                audio_path,
                int(structured),
            ),
        )
        conn.commit()
        entry_id = cur.lastrowid
    return get_entry(conn, entry_id)


def get_entry(conn: sqlite3.Connection, entry_id: int) -> dict | None:
    with _lock:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_entries(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Newest first. `query` does a simple substring match across the
    searchable text fields -- good enough for one person's journal; no need
    for FTS5 at this scale."""
    with _lock:
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                """
                SELECT * FROM entries
                WHERE title LIKE ? OR body LIKE ? OR summary LIKE ? OR raw_text LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (like, like, like, like, like, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]
