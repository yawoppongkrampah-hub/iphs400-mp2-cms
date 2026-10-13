"""Configuration, read from the environment (never hard-code secrets).

A `.env` file at the repository root is read first, so `cp .env.example .env` is
enough and no `--env-file` flag is needed. A variable that is already set in the
real environment always wins over the file, and nothing here prints a value.
`CMS_ENV_FILE` names a different file (the tests point it at nothing, so they never read yours).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# python-dotenv is already locked: uvicorn[standard], which pyproject declares, requires it.
# interpolate=False keeps a `$` in a password literal instead of expanding `${...}`.
load_dotenv(os.environ.get("CMS_ENV_FILE", ROOT / ".env"), override=False, interpolate=False)
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"
# Approved image files, added by the release-holder; `cms publish` copies them.
IMAGES = ROOT / "images"

# Values that are public because they sit in the repo. `cms serve` warns if one is in use.
PUBLIC_SECRET_KEYS = {"dev-only-not-for-production", "change-me-to-a-long-random-string"}
# `.env.example` starts every password and the key with this; seeding warns if one is still in use.
PLACEHOLDER_PREFIX = "change-me"


def is_placeholder_password(password: str) -> bool:
    return password.startswith(PLACEHOLDER_PREFIX)


SECRET_KEY = os.environ.get("CMS_SECRET_KEY", "dev-only-not-for-production")
DATABASE_PATH = Path(os.environ.get("CMS_DATABASE", ROOT / "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "African Student Association")
# The short name in the public header, so the full name appears once, in the Home hero.
SITE_SHORT_TITLE = os.environ.get("CMS_SITE_SHORT_TITLE", "ASA")
INSTAGRAM_URL = os.environ.get("CMS_INSTAGRAM_URL", "https://www.instagram.com/asa.kenyon/")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
