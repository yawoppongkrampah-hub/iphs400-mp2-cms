"""SQLite access. One short-lived connection per unit of work."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'editor')),
    display_name  TEXT    NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id                 INTEGER PRIMARY KEY,
    title              TEXT    NOT NULL,
    slug               TEXT    NOT NULL UNIQUE,
    body               TEXT    NOT NULL DEFAULT '',
    status             TEXT    NOT NULL DEFAULT 'draft'
                               CHECK (status IN ('draft', 'published')),
    author_id          INTEGER NOT NULL REFERENCES users(id),
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL,
    first_published_at TEXT
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the database, creating the file and tables on first use.

    Use as `with closing(connect(path)) as conn, conn:` so the connection is
    closed and the transaction commits (or rolls back on error).
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
