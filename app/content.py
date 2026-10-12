"""The Dashboard counts and the Content list: Posts and Pages seen together.

Nothing here knows about HTTP. Both are read fresh from the database on every
call, so they always match the content as it is now.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.db import connect

TYPES = ("post", "page")
STATUSES = ("draft", "published")


def counts(path: Path) -> dict[str, int]:
    """Posts and Pages by status, e.g. counts["published_posts"]."""
    result = {f"{status}_{kind}s": 0 for status in STATUSES for kind in TYPES}
    with closing(connect(path)) as conn:
        for kind in TYPES:
            for status, number in conn.execute(
                    f"SELECT status, COUNT(*) FROM {kind}s GROUP BY status"):
                result[f"{status}_{kind}s"] = number
    return result


def list_items(path: Path, *, kind: str | None = None,
               status: str | None = None) -> list[sqlite3.Row]:
    """Posts and Pages in one list, most recently updated first.

    `kind` ("post" or "page") and `status` ("draft" or "published") each narrow
    the list; None means no narrowing. Each row has: kind, id, title, status,
    author_name (None for a Page with no Author) and updated_at.
    """
    wanted = [k for k in TYPES if kind in (None, k)]
    selects = [
        f"SELECT '{k}' AS kind, {k}s.id AS id, {k}s.title AS title, "
        f"{k}s.status AS status, users.display_name AS author_name, "
        f"{k}s.updated_at AS updated_at "
        f"FROM {k}s LEFT JOIN users ON users.id = {k}s.author_id"
        + (f" WHERE {k}s.status = ?" if status else "")
        for k in wanted
    ]
    params = [status] * len(wanted) if status else []
    with closing(connect(path)) as conn:
        return conn.execute(
            " UNION ALL ".join(selects) + " ORDER BY updated_at DESC, kind, id DESC",
            params).fetchall()
