"""T01: sign in, sign out, Deactivated accounts, signed-out redirects, CSRF.

Seam 1 (the admin console over HTTP): these tests only look at what a visitor
sees and can do, plus the one stored-password check the security checklist asks
for (row 1).
"""
import logging
import sqlite3

import pytest

from app import accounts
from tests.conftest import DEMO_USERS, csrf_token, token_in


def sign_in(client, username, password, token=None, **kw):
    return client.post(
        "/login",
        data={"username": username, "password": password,
              "csrf_token": token if token is not None else csrf_token(client)},
        follow_redirects=False, **kw,
    )


# -- sign in ---------------------------------------------------------------

def test_sign_in_page_has_a_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_correct_credentials_reach_the_dashboard(client, role):
    user = DEMO_USERS[role]
    response = sign_in(client, user["username"], user["password"])
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "hello admin" in dashboard.text.lower()


def test_username_is_not_case_sensitive(client):
    response = sign_in(client, "ADMIN", DEMO_USERS["admin"]["password"])
    assert response.status_code == 303


def test_wrong_password_and_unknown_username_look_identical(client):
    wrong_pw = sign_in(client, "admin", "not-the-password")
    unknown = sign_in(client, "nobody-here", "not-the-password")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert "incorrect username or password" in wrong_pw.text.lower()

    def body(r):  # the CSRF token differs per response; nothing else may
        return r.text.replace(token_in(r.text), "")

    assert body(wrong_pw) == body(unknown)


def test_failed_sign_in_does_not_sign_in(client):
    sign_in(client, "admin", "not-the-password")
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


# -- Deactivated accounts --------------------------------------------------

def test_deactivated_account_cannot_sign_in(client, db_path):
    accounts.set_active(db_path, "editor", False)
    user = DEMO_USERS["editor"]
    response = sign_in(client, user["username"], user["password"])
    assert response.status_code == 401
    # Same message as a wrong password: it must not reveal the account exists.
    assert "incorrect username or password" in response.text.lower()
    assert client.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_deactivating_an_account_ends_its_existing_session(client_as, db_path):
    editor = client_as("editor")
    assert editor.get("/admin").status_code == 200
    accounts.set_active(db_path, "editor", False)
    response = editor.get("/admin", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


def test_reactivated_account_can_sign_in_again(client, db_path):
    accounts.set_active(db_path, "editor", False)
    accounts.set_active(db_path, "editor", True)
    user = DEMO_USERS["editor"]
    assert sign_in(client, user["username"], user["password"]).status_code == 303


# -- sign out --------------------------------------------------------------

def test_sign_out_ends_the_session(client_as):
    admin = client_as("admin")
    token = csrf_token(admin, "/admin")
    response = admin.post("/logout", data={"csrf_token": token},
                          follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    after = admin.get("/admin", follow_redirects=False)
    assert after.status_code in (302, 303)
    assert after.headers["location"] == "/login"


# -- signed out visitors ---------------------------------------------------

@pytest.mark.parametrize("path", [
    "/admin", "/admin/", "/admin/users", "/admin/posts/new",
    "/admin/does-not-exist",
])
def test_any_admin_address_sends_a_signed_out_visitor_to_sign_in(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


def test_signed_out_redirect_shows_no_admin_content(client):
    response = client.get("/admin")  # follows the redirect to the sign-in page
    assert "hello admin" not in response.text.lower()
    assert 'name="password"' in response.text


def test_public_home_needs_no_sign_in(client):
    assert client.get("/").status_code == 200


# -- CSRF ------------------------------------------------------------------

def test_sign_in_without_a_token_is_rejected(client):
    user = DEMO_USERS["admin"]
    response = client.post(
        "/login", data={"username": user["username"], "password": user["password"]},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert client.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_sign_in_with_a_wrong_token_is_rejected(client):
    user = DEMO_USERS["admin"]
    csrf_token(client)  # start a session so a real token exists
    response = sign_in(client, user["username"], user["password"], token="forged")
    assert response.status_code == 403


def test_sign_out_without_a_token_is_rejected_and_keeps_the_session(client_as):
    admin = client_as("admin")
    response = admin.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 403
    assert admin.get("/admin").status_code == 200


def test_a_token_from_another_session_is_rejected(client, client_as):
    admin = client_as("admin")
    foreign = csrf_token(admin, "/admin")
    other_session = client  # a different browser with its own cookie jar
    csrf_token(other_session)
    response = other_session.post("/logout", data={"csrf_token": foreign},
                                  follow_redirects=False)
    assert response.status_code == 403


def test_forms_carry_a_token(client_as, client):
    assert csrf_token(client, "/login")
    assert csrf_token(client_as("admin"), "/admin")  # the sign-out form


# -- passwords -------------------------------------------------------------

def test_stored_passwords_are_argon2_hashes(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT username, password_hash FROM users").fetchall()
    assert {r[0] for r in rows} == {"admin", "editor"}
    plain = {u["password"] for u in DEMO_USERS.values()}
    for _, stored in rows:
        assert stored.startswith("$argon2")
        assert not any(p in stored for p in plain)


def test_no_response_or_log_contains_a_plain_password(client, caplog):
    caplog.set_level(logging.DEBUG)
    user = DEMO_USERS["admin"]
    secret = user["password"]
    responses = [
        sign_in(client, user["username"], "wrong-" + secret),
        sign_in(client, user["username"], secret),
        client.get("/admin"),
    ]
    for r in responses:
        assert secret not in r.text
        assert secret not in str(r.headers)
    assert secret not in caplog.text and ("wrong-" + secret) not in caplog.text


def test_session_cookie_is_http_only(client):
    user = DEMO_USERS["admin"]
    response = sign_in(client, user["username"], user["password"])
    assert "httponly" in response.headers["set-cookie"].lower()
