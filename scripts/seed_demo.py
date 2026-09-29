#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

Creates the demo Admin ("admin") and Editor ("editor") if they do not exist, with
passwords from CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD. As you build content
types, extend this so it also creates:
  - a few posts and pages, at least one draft and one published

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import sys
from contextlib import closing

from app import accounts, posts, settings
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
    seed_demo_posts(settings.DATABASE_PATH)
    print("Demo accounts ready: 'admin' and 'editor' (passwords from your environment). "
          "Demo Posts ready: one Published, one Draft.")
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
