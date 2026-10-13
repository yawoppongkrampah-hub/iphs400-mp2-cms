"""Configuration, read from the environment (never hard-code secrets)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"
# Approved image files, added by the release-holder; `cms publish` copies them.
IMAGES = ROOT / "images"

SECRET_KEY = os.environ.get("CMS_SECRET_KEY", "dev-only-not-for-production")
DATABASE_PATH = Path(os.environ.get("CMS_DATABASE", ROOT / "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "African Student Association")
# The short name in the public header, so the full name appears once, in the Home hero.
SITE_SHORT_TITLE = os.environ.get("CMS_SITE_SHORT_TITLE", "ASA")
INSTAGRAM_URL = os.environ.get("CMS_INSTAGRAM_URL", "https://www.instagram.com/asa.kenyon/")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
