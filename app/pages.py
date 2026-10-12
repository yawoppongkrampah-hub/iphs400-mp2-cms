"""Pages: permanent content that appears in the public Navigation once Published.

Nothing here knows about HTTP. Unlike a Post, a Page's slug is entered by the
Admin, and each Page is written to the site root as `<slug>.html`.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.db import connect
from app.posts import _now, slugify


class PageError(ValueError):
    """A request about a Page that cannot be honoured (shown to the person)."""


class PageTitleRequired(PageError):
    pass


class PageSlugInvalid(PageError):
    pass


class PageSlugTaken(PageError):
    pass


# Files the export already writes at the site root; a Page may not overwrite them.
RESERVED_SLUGS = frozenset({"index", "announcements"})

_WITH_AUTHOR = ("SELECT pages.*, users.display_name AS author_name "
                "FROM pages LEFT JOIN users ON users.id = pages.author_id")


def _clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise PageTitleRequired("A Page needs a title.")
    return title


def _clean_slug(slug: str) -> str:
    slug = slugify(slug)
    if not slug:
        raise PageSlugInvalid("A slug needs at least one letter or number.")
    if slug in RESERVED_SLUGS:
        raise PageSlugInvalid(f"'{slug}' is used by the site itself. Choose another slug.")
    return slug


def create(path: Path, *, title: str, slug: str, body: str,
           author_id: int | None = None) -> int:
    title, slug = _clean_title(title), _clean_slug(slug)
    now = _now()
    try:
        with closing(connect(path)) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO pages (title, slug, body, author_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)", (title, slug, body, author_id, now, now))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise PageSlugTaken(f"Another Page already uses '{slug}'.") from None


def get(path: Path, page_id: int) -> sqlite3.Row | None:
    with closing(connect(path)) as conn:
        return conn.execute(f"{_WITH_AUTHOR} WHERE pages.id = ?", (page_id,)).fetchone()


def list_all(path: Path) -> list[sqlite3.Row]:
    with closing(connect(path)) as conn:
        return conn.execute(f"{_WITH_AUTHOR} ORDER BY pages.id").fetchall()


def list_published(path: Path) -> list[sqlite3.Row]:
    """Published Pages only, in the order they were created: the Navigation order."""
    with closing(connect(path)) as conn:
        return conn.execute("SELECT title, slug, body FROM pages "
                            "WHERE status = 'published' ORDER BY id").fetchall()


def update_body(path: Path, page_id: int, body: str) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE pages SET body = ?, updated_at = ? WHERE id = ?",
                     (body, _now(), page_id))


def retitle(path: Path, page_id: int, title: str) -> None:
    title = _clean_title(title)
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE pages SET title = ?, updated_at = ? WHERE id = ?",
                     (title, _now(), page_id))


def change_slug(path: Path, page_id: int, slug: str) -> None:
    slug = _clean_slug(slug)
    try:
        with closing(connect(path)) as conn, conn:
            conn.execute("UPDATE pages SET slug = ?, updated_at = ? WHERE id = ?",
                         (slug, _now(), page_id))
    except sqlite3.IntegrityError:
        raise PageSlugTaken(f"Another Page already uses '{slug}'.") from None


def publish(path: Path, page_id: int) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE pages SET status = 'published' WHERE id = ?", (page_id,))


def unpublish(path: Path, page_id: int) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE pages SET status = 'draft' WHERE id = ?", (page_id,))


def delete(path: Path, page_id: int) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
