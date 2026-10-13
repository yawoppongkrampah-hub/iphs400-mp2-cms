"""T08: the demo rebuilds from `.env.example`, and a clean setup reaches a working sign-in.

Seam 3 (the `cms` command and scripts): run `scripts/seed_demo.py` as a new
process, in an empty folder, with only the values in `.env.example`, then sign
in to the console it built. No password, `.env` or database is read from the repo.
"""
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.cli import main
from app.main import create_app
from tests.conftest import csrf_token

ROOT = Path(__file__).resolve().parents[1]


def env_example() -> dict[str, str]:
    values = {}
    for line in (ROOT / ".env.example").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip().strip('"')
    return values


def run_seed(folder, **override):
    """The README's setup, in an empty folder: copy .env.example to .env, then seed with uv.

    `uv` reads the file itself, so a line it cannot parse fails here as it would for a grader.
    """
    text = (ROOT / ".env.example").read_text()
    for name, value in override.items():
        text = re.sub(rf"(?m)^{name}=.*$", f"{name}={value}", text)
    (folder / ".env").write_text(text)
    env = {k: v for k, v in os.environ.items() if not k.startswith("CMS_")}
    return subprocess.run(
        ["uv", "run", "--no-sync", "--project", str(ROOT), "--env-file", ".env",
         "python", str(ROOT / "scripts" / "seed_demo.py")],
        cwd=folder, env=env, capture_output=True, text=True)


def rows(path, sql):
    with sqlite3.connect(path) as conn:
        return conn.execute(sql).fetchall()


def sign_in(path, username, password):
    client = TestClient(create_app(database=path))
    response = client.post("/login", data={"username": username, "password": password,
                                           "csrf_token": csrf_token(client)},
                           follow_redirects=False)
    return client, response


@pytest.fixture
def demo(tmp_path):
    result = run_seed(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    return tmp_path / "cms.db", result


def test_seed_runs_clean_from_env_example(demo):
    path, result = demo
    assert result.stderr == ""                       # includes uv's "Failed to parse environment file"
    assert path.exists()


def test_seed_has_both_roles_and_one_deactivated_account(demo):
    path, _ = demo
    assert rows(path, "SELECT role, active FROM users WHERE username IN ('admin','editor') "
                      "ORDER BY username") == [("admin", 1), ("editor", 1)]
    assert rows(path, "SELECT COUNT(*) FROM users WHERE active = 0") == [(1,)]
    assert rows(path, "SELECT COUNT(*) FROM users") == [(3,)]


def test_seed_has_published_and_draft_posts_and_pages(demo):
    path, _ = demo
    for table in ("posts", "pages"):
        statuses = {s for (s,) in rows(path, f"SELECT status FROM {table}")}
        assert statuses == {"published", "draft"}, table


def test_seed_holds_no_personal_data_and_no_claim_beyond_the_brief(demo):
    path, _ = demo
    text = " ".join(str(v) for table in ("users", "posts", "pages")
                    for row in rows(path, f"SELECT * FROM {table}") for v in row
                    if not str(v).startswith("$argon2"))
    assert "@" not in text                                        # no email addresses
    assert "demo placeholder" in text.lower()
    for claim in ("founded", "president", "treasurer", "meets every", "since 19", "since 20"):
        assert claim not in text.lower()


def test_seed_passwords_are_hashed_and_never_printed(demo):
    path, result = demo
    for password in (env_example()["CMS_ADMIN_PASSWORD"], env_example()["CMS_EDITOR_PASSWORD"]):
        assert password not in result.stdout + result.stderr
        assert password.encode() not in path.read_bytes()
    assert all(h.startswith("$argon2") for (h,) in rows(path, "SELECT password_hash FROM users"))


def test_seed_can_run_again_without_changing_anything(demo, tmp_path):
    path, _ = demo
    before = rows(path, "SELECT username, role, active, display_name FROM users")
    counts = rows(path, "SELECT (SELECT COUNT(*) FROM posts), (SELECT COUNT(*) FROM pages)")
    assert run_seed(tmp_path).returncode == 0
    assert rows(path, "SELECT username, role, active, display_name FROM users") == before
    assert rows(path, "SELECT (SELECT COUNT(*) FROM posts), (SELECT COUNT(*) FROM pages)") == counts


def test_clean_setup_reaches_a_working_sign_in_as_both_roles(demo):
    path, _ = demo
    for username, variable in (("admin", "CMS_ADMIN_PASSWORD"), ("editor", "CMS_EDITOR_PASSWORD")):
        client, response = sign_in(path, username, env_example()[variable])
        assert response.status_code == 303 and response.headers["location"] == "/admin"
        assert client.get("/admin").status_code == 200


def test_the_deactivated_demo_account_cannot_sign_in(demo):
    path, _ = demo
    (username,) = rows(path, "SELECT username FROM users WHERE active = 0")[0]
    for guess in (env_example()["CMS_ADMIN_PASSWORD"], env_example()["CMS_EDITOR_PASSWORD"],
                  "anything-at-all"):
        _, response = sign_in(path, username, guess)
        assert response.status_code != 303


def test_seed_says_when_a_placeholder_password_is_still_in_use(demo, tmp_path):
    _, result = demo
    assert "placeholder" in result.stdout.lower() and ".env.example" in result.stdout
    other = tmp_path / "other"
    other.mkdir()
    quiet = run_seed(other, CMS_ADMIN_PASSWORD="a-long-private-passphrase-1",
                     CMS_EDITOR_PASSWORD="another-long-private-passphrase-2")
    assert quiet.returncode == 0
    assert "change-me" not in quiet.stdout and "placeholder password" not in quiet.stdout.lower()


# -- the signing key ---------------------------------------------------------------

@pytest.mark.parametrize("key", ["dev-only-not-for-production", "change-me-to-a-long-random-string"])
def test_serve_warns_loudly_when_the_signing_key_is_a_public_one(key, monkeypatch, capsys):
    monkeypatch.setattr(settings, "SECRET_KEY", key)
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    assert main(["serve"]) == 0
    assert "CMS_SECRET_KEY" in capsys.readouterr().err


def test_serve_is_quiet_with_a_private_signing_key(monkeypatch, capsys):
    monkeypatch.setattr(settings, "SECRET_KEY", "x" * 48)
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    assert main(["serve"]) == 0
    assert capsys.readouterr().err == ""


def test_create_admin_says_when_the_password_is_a_placeholder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "cli.db")
    monkeypatch.setenv("CMS_ADMIN_PASSWORD", env_example()["CMS_ADMIN_PASSWORD"])
    assert main(["create-admin", "--username", "boss", "--display-name", "X"]) == 0
    out = capsys.readouterr().out
    assert "placeholder" in out.lower() and env_example()["CMS_ADMIN_PASSWORD"] not in out

    monkeypatch.setenv("CMS_ADMIN_PASSWORD", "a-long-private-passphrase-1")
    assert main(["create-admin", "--username", "boss2", "--display-name", "X"]) == 0
    assert "placeholder" not in capsys.readouterr().out.lower()


def test_a_password_that_only_contains_the_placeholder_prefix_is_not_flagged(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    result = run_seed(other, CMS_ADMIN_PASSWORD="my-change-me-passphrase-1",
                      CMS_EDITOR_PASSWORD="another-long-private-passphrase-2")
    assert "placeholder password" not in result.stdout.lower()


def test_git_tracks_no_env_file_database_or_state():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True).stdout.split()
    assert [f for f in tracked if f.endswith((".db", ".env")) or f == ".env"] == []
    assert ".env.example" in tracked


# -- the release checklist's two limits, as behaviour ---------------------------------

def test_no_screen_or_route_accepts_a_file_so_an_editor_cannot_add_an_image(client_as):
    """The checklist says an Editor cannot add an image file alone. There is nothing to add one with."""
    editor = client_as("editor")
    for url in ("/admin", "/admin/posts/new", "/admin/posts", "/admin/pages", "/admin/content"):
        html = editor.get(url).text
        assert 'type="file"' not in html and "multipart" not in html, url
    assert "multipart/form-data" not in json.dumps(editor.app.openapi())


def checklist_relative_path_command():
    text = (ROOT / "docs" / "release-checklist.md").read_text()
    return re.search(r"^\s+(grep -rEn '[^\n]+' site/)\s*$", text, re.M).group(1)


def test_the_checklists_relative_path_check_is_quiet_on_a_real_export_and_catches_a_bad_one(
        db_path, tmp_path):
    from app.publish import render_site
    out = render_site(tmp_path / "site", database=db_path)
    command = shlex.split(checklist_relative_path_command().replace("site/", str(out) + "/"))
    clean = subprocess.run(command, capture_output=True, text=True)
    assert clean.returncode == 1 and clean.stdout == ""          # grep: no match, nothing printed

    (out / "bad.html").write_text('<a href="/admin">x</a><img src="/images/a.png">')
    caught = subprocess.run(command, capture_output=True, text=True)
    assert caught.returncode == 0 and "bad.html" in caught.stdout
