"""Render the public site into site/ as plain HTML.

Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
     Pages one folder down (posts/) reach the site root with a `root` of "../".
"""
from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import settings
from app.db import connect
from app.rendering import render_body

# The wording comes from notes/client-brief.md. Make no other claim about ASA.
WELCOME = (
    "ASA is a Kenyon student group primarily for African students and students "
    "with African backgrounds, while welcoming anyone interested in African "
    "cultures and community."
)
HOME_ANNOUNCEMENTS = 5

CSS = """/* Minimal starter styles — make them yours. */
:root { color-scheme: light dark; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; }
header { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; align-items: baseline; }
header a { font-weight: 700; text-decoration: none; }
a:focus-visible { outline: 3px solid currentColor; outline-offset: 2px; }
main { margin-block: 2rem; }
img { max-width: 100%; height: auto; }
.card { border: 1px solid; border-radius: 0.5rem; padding: 0.75rem 1rem; margin-block: 1rem; }
.card-title { margin: 0; font-size: 1.2rem; }
.meta { margin: 0.25rem 0 0; font-size: 0.9rem; opacity: 0.8; }
"""


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _day(timestamp: str) -> tuple[str, str]:
    """A stored UTC timestamp as ("2026-09-28", "28 September 2026")."""
    moment = datetime.fromisoformat(timestamp)
    return moment.date().isoformat(), f"{moment.day} {moment:%B %Y}"


def _published_posts(database: Path) -> list[dict]:
    """Published Posts only, newest First-published date first.

    Ordered by First-published date, not by edit time, so a correction never
    moves a Post. The byline is the Author's Display name; the Username is not
    even selected.
    """
    with closing(connect(database)) as conn:
        rows = conn.execute(
            "SELECT posts.title, posts.slug, posts.body, posts.updated_at, "
            "posts.first_published_at, users.display_name AS author_name "
            "FROM posts JOIN users ON users.id = posts.author_id "
            "WHERE posts.status = 'published' "
            "ORDER BY posts.first_published_at DESC, posts.id DESC"
        ).fetchall()
    return [_post_for_template(row) for row in rows]


def _post_for_template(row: sqlite3.Row) -> dict:
    posted_iso, posted_label = _day(row["first_published_at"])
    post = {
        "title": row["title"], "slug": row["slug"], "author_name": row["author_name"],
        "body_html": render_body(row["body"]),
        "posted_iso": posted_iso, "posted_label": posted_label,
        "updated_iso": None, "updated_label": None,
    }
    if row["updated_at"] > row["first_published_at"]:
        post["updated_iso"], post["updated_label"] = _day(row["updated_at"])
    return post


def render_site(out: Path | None = None, database: Path | None = None) -> Path:
    out = out or settings.SITE
    database = database or settings.DATABASE_PATH
    if out.exists():
        shutil.rmtree(out)
    (out / "posts").mkdir(parents=True)
    env = environment()
    published = _published_posts(database)
    common = {"site_title": settings.SITE_TITLE}

    def write(name: str, template: str, **context) -> None:
        (out / name).write_text(env.get_template(template).render(
            **common, **context))

    (out / "style.css").write_text(CSS)
    write("index.html", "public/home.html", title=settings.SITE_TITLE, root="",
          welcome=WELCOME, posts=published[:HOME_ANNOUNCEMENTS])
    write("announcements.html", "public/announcements.html",
          title=f"Announcements · {settings.SITE_TITLE}", root="", posts=published)
    for post in published:
        write(f"posts/{post['slug']}.html", "public/post.html", root="../", post=post,
              title=post["title"])
    return out
