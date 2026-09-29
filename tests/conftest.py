"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role, so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)

Every test gets its own throwaway SQLite database, seeded with the two demo
accounts below (the same ones scripts/seed_demo.py creates). Accounts sign in
with a username, not an email address.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import accounts
from app.main import create_app

# Matches scripts/seed_demo.py. Passwords come from the environment there; in
# tests they are fixed and meaningless.
DEMO_USERS = {
    "admin": {"username": "admin", "password": "test-admin-pw"},
    "editor": {"username": "editor", "password": "test-editor-pw"},
}

_TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


def csrf_token(client: TestClient, path: str = "/login") -> str:
    """Read the CSRF token from the form on `path` (what a browser would submit)."""
    return token_in(client.get(path).text)


def token_in(html: str) -> str:
    match = _TOKEN.search(html)
    assert match, "no csrf_token field in the page"
    return match.group(1)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    accounts.seed_demo_accounts(
        path,
        admin_password=DEMO_USERS["admin"]["password"],
        editor_password=DEMO_USERS["editor"]["password"],
    )
    return path


@pytest.fixture
def client(db_path) -> TestClient:
    return TestClient(create_app(database=db_path))


@pytest.fixture
def client_as(db_path):
    """Return a factory: client_as("editor") -> a logged-in TestClient."""

    def _login(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(create_app(database=db_path))
        response = c.post(
            "/login",
            data={"username": user["username"], "password": user["password"],
                  "csrf_token": csrf_token(c)},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303), (
            f"Login as {role} failed with {response.status_code}")
        return c

    return _login
