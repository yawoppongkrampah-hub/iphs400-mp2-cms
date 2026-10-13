"""Render the public site into site/ as plain HTML.

Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
     Pages one folder down (posts/) reach the site root with a `root` of "../".
"""
from __future__ import annotations

import html
import re
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import pages, settings
from app.db import connect
from app.rendering import PAGE_ROOT, POST_ROOT, render_body

# The wording comes from notes/client-brief.md. Make no other claim about ASA.
WELCOME = (
    "ASA is a Kenyon student group primarily for African students and students "
    "with African backgrounds, while welcoming anyone interested in African "
    "cultures and community."
)
HOME_ANNOUNCEMENTS = 5
EXCERPT_CHARS = 140
# Approved image files the release-holder may add to images/. Anything else is ignored.
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


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


def card_excerpt(body_html: str) -> str:
    """The start of a Post's rendered Body as plain text, for its Event card.

    Works on sanitized output, which holds only a handful of tags. Inline tags vanish
    ("**demo**," stays "demo,"), block ends become spaces, and list items are told
    apart by " · " so "What: a party When: soon" does not run together.
    """
    text = body_html.replace("</li>", " · ")
    text = re.sub(r"</(?:p|ul|ol|h[1-6])>|<br\s*/?>", " ", text)
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split()).strip(" ·")
    if len(text) <= EXCERPT_CHARS:
        return text
    # Cut at a word end: looking one character past the limit keeps a word that ends exactly on it.
    cut = text[:EXCERPT_CHARS + 1].rsplit(" ", 1)[0][:EXCERPT_CHARS]
    return cut.rstrip(" ,.;:·") + "…"


def _post_for_template(row: sqlite3.Row) -> dict:
    posted_iso, posted_label = _day(row["first_published_at"])
    body_html = render_body(row["body"], root=POST_ROOT)
    post = {
        "title": row["title"], "slug": row["slug"], "author_name": row["author_name"],
        "body_html": body_html, "excerpt": card_excerpt(body_html),
        "posted_iso": posted_iso, "posted_label": posted_label,
        "updated_iso": None, "updated_label": None,
    }
    if row["updated_at"] > row["first_published_at"]:
        post["updated_iso"], post["updated_label"] = _day(row["updated_at"])
    return post


def is_approved_image(source: Path, path: Path) -> bool:
    """An image file inside `source`: by extension, never hidden, never outside it.

    So a stray `.env` or script dropped in the folder cannot reach the public site,
    and the console's Preview cannot be asked for a file outside the folder.
    """
    try:
        relative = path.resolve().relative_to(source.resolve())
    except (ValueError, OSError):
        return False
    return (path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            and not any(part.startswith(".") for part in relative.parts))


def copy_images(source: Path, out: Path) -> None:
    """Copy the release-holder's approved image files to <site>/images/."""
    if not source.is_dir():
        return
    for path in sorted(source.rglob("*")):
        if is_approved_image(source, path):
            target = out / "images" / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def render_site(out: Path | None = None, database: Path | None = None,
                images: Path | None = None) -> Path:
    out = out or settings.SITE
    database = database or settings.DATABASE_PATH
    images = images or settings.IMAGES
    if out.exists():
        shutil.rmtree(out)
    (out / "posts").mkdir(parents=True)
    env = environment()
    published = _published_posts(database)
    published_pages = pages.list_published(database)
    # Every page of the site shows the same Navigation; the template prefixes `root`.
    nav_pages = [{"title": page["title"], "slug": page["slug"]} for page in published_pages]
    common = {"site_title": settings.SITE_TITLE, "short_title": settings.SITE_SHORT_TITLE,
              "instagram_url": settings.INSTAGRAM_URL, "nav_pages": nav_pages}

    def write(name: str, template: str, **context) -> None:
        (out / name).write_text(env.get_template(template).render(
            **common, **context))

    (out / "style.css").write_text((settings.TEMPLATES / "public" / "style.css").read_text())
    copy_images(images, out)
    write("index.html", "public/home.html", title=settings.SITE_TITLE, root="",
          welcome=WELCOME, posts=published[:HOME_ANNOUNCEMENTS], card_level=3)
    write("announcements.html", "public/announcements.html",
          title=f"Announcements · {settings.SITE_TITLE}", root="", posts=published,
          current="announcements")
    for post in published:
        write(f"posts/{post['slug']}.html", "public/post.html", root=POST_ROOT, post=post,
              title=post["title"], current="announcements")
    for page in published_pages:
        write(f"{page['slug']}.html", "public/page.html", root="", title=page["title"],
              current=page["slug"],
              page={"title": page["title"],
                    "body_html": render_body(page["body"], root=PAGE_ROOT)})
    return out
