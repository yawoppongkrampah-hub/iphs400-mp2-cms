"""Posts: the data rules (slugs, Author, First-published date).

Nothing here knows about HTTP. Slugs are made once from the title and only
change through `change_slug`, which the routes reserve for the Admin.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.db import connect


class PostError(ValueError):
    """A request about a Post that cannot be honoured (shown to the person)."""


class TitleRequired(PostError):
    pass


class SlugInvalid(PostError):
    pass


class SlugTaken(PostError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _unique_slug(conn: sqlite3.Connection, base: str) -> str:
    slug, number = base, 1
    while conn.execute("SELECT 1 FROM posts WHERE slug = ?", (slug,)).fetchone():
        number += 1
        slug = f"{base}-{number}"
    return slug


def _clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise TitleRequired("A Post needs a title.")
    return title


_WITH_AUTHOR = ("SELECT posts.*, users.display_name AS author_name "
                "FROM posts JOIN users ON users.id = posts.author_id")


def create(path: Path, *, title: str, body: str, author_id: int) -> int:
    title = _clean_title(title)
    now = _now()
    with closing(connect(path)) as conn, conn:
        slug = _unique_slug(conn, slugify(title) or "post")
        cursor = conn.execute(
            "INSERT INTO posts (title, slug, body, author_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, slug, body, author_id, now, now),
        )
        return cursor.lastrowid


def get(path: Path, post_id: int) -> sqlite3.Row | None:
    with closing(connect(path)) as conn:
        return conn.execute(f"{_WITH_AUTHOR} WHERE posts.id = ?", (post_id,)).fetchone()


def list_all(path: Path) -> list[sqlite3.Row]:
    with closing(connect(path)) as conn:
        return conn.execute(f"{_WITH_AUTHOR} ORDER BY posts.updated_at DESC, posts.id DESC"
                            ).fetchall()


def update(path: Path, post_id: int, *, title: str, body: str) -> None:
    title = _clean_title(title)
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE posts SET title = ?, body = ?, updated_at = ? WHERE id = ?",
                     (title, body, _now(), post_id))


def publish(path: Path, post_id: int) -> None:
    """Mark Published. The First-published date is set once and never moved."""
    with closing(connect(path)) as conn, conn:
        conn.execute(
            "UPDATE posts SET status = 'published', "
            "first_published_at = COALESCE(first_published_at, ?) WHERE id = ?",
            (_now(), post_id))


def unpublish(path: Path, post_id: int) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE posts SET status = 'draft' WHERE id = ?", (post_id,))


def delete(path: Path, post_id: int) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))


def change_slug(path: Path, post_id: int, slug: str) -> None:
    slug = slugify(slug)
    if not slug:
        raise SlugInvalid("A slug needs at least one letter or number.")
    try:
        with closing(connect(path)) as conn, conn:
            conn.execute("UPDATE posts SET slug = ? WHERE id = ?", (slug, post_id))
    except sqlite3.IntegrityError:
        raise SlugTaken(f"Another Post already uses '{slug}'.") from None
