#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

Creates the demo Admin ("admin") and Editor ("editor") if they do not exist, with
passwords from CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD. As you build content
types, extend this so it also creates:
  - a few posts and pages, at least one draft and one published (done: Posts and Pages)

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import secrets
import sys
from contextlib import closing
from pathlib import Path

from app import accounts, pages, posts, settings
from app.db import connect


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    accounts.seed_demo_accounts(
        settings.DATABASE_PATH, admin_password=admin_pw, editor_password=editor_pw)
    seed_demo_deactivated(settings.DATABASE_PATH)
    seed_demo_posts(settings.DATABASE_PATH)
    seed_demo_pages(settings.DATABASE_PATH)
    print("Demo accounts ready: 'admin' and 'editor' (passwords from your environment), "
          "and one Deactivated account that cannot sign in. "
          "Demo Posts ready: one Published, one Draft. "
          "Demo Pages ready: About ASA, Resources and Photos Published, one Draft.")
    if any(settings.is_placeholder_password(pw) for pw in (admin_pw, editor_pw)):
        print("NOTE: a demo account is using the placeholder password from .env.example. "
              "That is fine on your own laptop; choose your own in .env before anyone "
              "else can reach the console.")
    return 0


def seed_demo_deactivated(path: Path) -> None:
    """One Deactivated account, so the demo can show that a former member cannot sign in.

    Its password is random and thrown away: nobody, including the demo, can sign in as it.
    """
    try:
        accounts.create_account(path, username="former-member", password=secrets.token_urlsafe(24),
                                role="editor", display_name="Former member (demo)")
    except accounts.UsernameTaken:
        return
    accounts.set_active(path, "former-member", False)


# Placeholders only: no claim about ASA's real events, dates, places or people.
DEMO_POSTS = [
    ("Afrobeat event (demo placeholder)", True,
     "This is a **demo placeholder**, not a real ASA announcement.\n\n"
     "- **What:** an Afrobeat event\n- **When:** to be announced\n"
     "- **Where:** to be announced\n- **Who can attend:** to be announced\n"),
    ("Draft idea (demo placeholder)", False,
     "A draft that must never appear on the public site.\n"),
]


def seed_demo_posts(path) -> None:
    """Create the demo Posts once, written by the demo Editor."""
    with closing(connect(path)) as conn:
        if conn.execute("SELECT 1 FROM posts").fetchone():
            return
        editor = conn.execute(
            "SELECT id FROM users WHERE username = 'editor'").fetchone()["id"]
    for title, published, body in DEMO_POSTS:
        post_id = posts.create(path, title=title, body=body, author_id=editor)
        if published:
            posts.publish(path, post_id)


# Starter Pages: placeholders only, with no claim about ASA. Listed in Navigation order.
DEMO_PAGES = [
    ("About ASA", "about-asa", True,
     "This is a **demo placeholder** Page, not ASA's real About page.\n\n"
     "ASA's own description of itself will replace this text.\n"),
    ("Resources", "resources", True,
     "This is a **demo placeholder** Page, not a real list of ASA resources.\n\n"
     "Cultural resources will be listed here.\n"),
    ("Photos", "photos", True,
     "This is a **demo placeholder** Page.\n\n"
     "Actual event photos will be added when ASA has permission to use them.\n\n"
     "## Illustrative placeholders\n\n"
     "![Illustration: three overlapping circles in red, gold and green]"
     "(images/demo-illustration-1.svg)\n\n"
     "*Illustrative placeholder, not a photo of a real ASA event.*\n\n"
     "![Illustration: wavy red, gold and cream lines on a green background]"
     "(images/demo-illustration-2.svg)\n\n"
     "*Illustrative placeholder, not a photo of a real ASA event.*\n\n"
     "![Illustration: a row of diamond shapes on a dark background]"
     "(images/demo-illustration-3.svg)\n\n"
     "*Illustrative placeholder, not a photo of a real ASA event.*\n"),
    ("Get involved (draft)", "get-involved", False,
     "A draft Page that must never appear on the public site or in the Navigation.\n"),
]


def seed_demo_pages(path) -> None:
    """Create the starter Pages once, created by the demo Admin."""
    with closing(connect(path)) as conn:
        if conn.execute("SELECT 1 FROM pages").fetchone():
            return
        admin = conn.execute(
            "SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
    for title, slug, published, body in DEMO_PAGES:
        page_id = pages.create(path, title=title, slug=slug, body=body, author_id=admin)
        if published:
            pages.publish(path, page_id)


if __name__ == "__main__":
    sys.exit(main())
