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

from app import accounts, settings


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    accounts.seed_demo_accounts(
        settings.DATABASE_PATH, admin_password=admin_pw, editor_password=editor_pw)
    print("Demo accounts ready: 'admin' and 'editor' (passwords from your environment). "
          "No content types exist yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
