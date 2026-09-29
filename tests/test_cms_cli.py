"""Seam 3: a small smoke test of the `cms` command (first-Admin creation)."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.cli import main
from app.main import create_app
from tests.conftest import csrf_token


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    path = tmp_path / "cli.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", path)
    return path


def test_create_admin_reads_the_password_from_the_environment(
        cli_db, monkeypatch, capsys):
    monkeypatch.setenv("CMS_ADMIN_PASSWORD", "s3cret-from-env")
    code = main(["create-admin", "--username", "boss", "--display-name", "ASA Leadership"])
    out = capsys.readouterr()
    assert code == 0
    assert "s3cret-from-env" not in out.out + out.err

    with sqlite3.connect(cli_db) as conn:
        row = conn.execute(
            "SELECT role, display_name, active, password_hash FROM users "
            "WHERE username = 'boss'").fetchone()
    assert row[:3] == ("admin", "ASA Leadership", 1)
    assert row[3].startswith("$argon2") and "s3cret-from-env" not in row[3]

    # ...and that account can actually sign in through the console.
    client = TestClient(create_app(database=cli_db))
    response = client.post(
        "/login", data={"username": "boss", "password": "s3cret-from-env",
                        "csrf_token": csrf_token(client)},
        follow_redirects=False)
    assert response.status_code == 303


def test_create_admin_refuses_without_a_password(cli_db, monkeypatch, capsys):
    monkeypatch.delenv("CMS_ADMIN_PASSWORD", raising=False)
    assert main(["create-admin", "--username", "boss", "--display-name", "X"]) == 1
    assert "CMS_ADMIN_PASSWORD" in capsys.readouterr().out
    assert not cli_db.exists() or not sqlite3.connect(cli_db).execute(
        "SELECT 1 FROM users").fetchall()


def test_create_admin_refuses_a_taken_username(cli_db, monkeypatch, capsys):
    monkeypatch.setenv("CMS_ADMIN_PASSWORD", "s3cret-from-env")
    assert main(["create-admin", "--username", "boss", "--display-name", "X"]) == 0
    assert main(["create-admin", "--username", "BOSS", "--display-name", "Y"]) == 1
    assert "already exists" in capsys.readouterr().out


def test_publish_command_writes_the_site_from_published_posts(
        cli_db, tmp_path, monkeypatch, capsys):
    from app import accounts, posts

    accounts.seed_demo_accounts(cli_db, admin_password="test-admin-pw",
                                editor_password="test-editor-pw")
    live = posts.create(cli_db, title="Afrobeat Night", body="What: music", author_id=2)
    posts.publish(cli_db, live)
    posts.create(cli_db, title="Unfinished Idea", body="draft", author_id=2)
    site = tmp_path / "site"
    monkeypatch.setattr(settings, "SITE", site)

    assert main(["publish"]) == 0
    assert (site / "posts" / "afrobeat-night.html").exists()
    assert not (site / "posts" / "unfinished-idea.html").exists()
    assert "Wrote" in capsys.readouterr().out
