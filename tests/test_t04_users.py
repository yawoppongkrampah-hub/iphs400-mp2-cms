"""T04: the Admin manages accounts.

Seam 1 (the admin console over HTTP) for everything an Admin or Editor sees and
can do; Seam 2 (the published site on disk) for the byline after a Display name
change. Nothing here looks at internal functions.
"""
import logging
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.publish import render_site
from tests.conftest import DEMO_USERS, csrf_token, token_in
from tests.test_t02_posts import create_post, is_refusal, post_to

NEW_PASSWORD = "brand-new-secret-1"
RESET_PASSWORD = "reset-secret-xyz-2"


def create_account(admin, *, username="newbie", password="newbie-pass-1",
                   role="editor", display_name="New Member"):
    response = post_to(admin, "/admin/users", username=username, password=password,
                       role=role, display_name=display_name)
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/users/(\d+)", response.headers["location"]).group(1))


def account_page(admin, user_id):
    response = admin.get(f"/admin/users/{user_id}")
    assert response.status_code == 200
    return response.text


def shown(html, name):
    """The text of <... id="account-NAME">...</...> on an account page."""
    match = re.search(rf'id="account-{name}"[^>]*>\s*([^<]+?)\s*<', html)
    assert match, f"account-{name} is not shown"
    return match.group(1)


def user_id_of(db_path, username):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT id FROM users WHERE username = ?",
                            (username,)).fetchone()[0]


def sign_in(db_path, username, password):
    """A fresh client signing in; returns (client, sign-in response)."""
    client = TestClient(create_app(database=db_path))
    response = client.post(
        "/login", data={"username": username, "password": password,
                        "csrf_token": csrf_token(client)}, follow_redirects=False)
    return client, response


def can_sign_in(db_path, username, password):
    return sign_in(db_path, username, password)[1].status_code in (302, 303)


def author_post(db_path, username, title="Afrobeat Night"):
    """A Published Post written by `username`, made through the app."""
    client, _ = sign_in(db_path, username, "newbie-pass-1")
    post_id = create_post(client, title, "What: music")
    assert post_to(client, f"/admin/posts/{post_id}/publish").status_code == 303
    return post_id


# -- creating accounts -------------------------------------------------------

def test_admin_creates_an_account_that_can_sign_in(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             role="editor", display_name="Amara O.")
    html = account_page(admin, user_id)
    assert shown(html, "role") == "Editor"
    assert shown(html, "display-name") == "Amara O."
    assert shown(html, "status") == "Active"
    assert "Amara O." in admin.get("/admin/users").text
    assert can_sign_in(db_path, "amara", "amara-pass-99")


def test_admin_can_create_another_admin(client_as, db_path):
    admin = client_as("admin")
    create_account(admin, username="second", password="second-pass-1", role="admin",
                   display_name="Second Leader")
    client, _ = sign_in(db_path, "second", "second-pass-1")
    assert client.get("/admin/users").status_code == 200


def test_a_new_account_starts_as_a_writer_not_an_admin_unless_asked(client_as, db_path):
    admin = client_as("admin")
    create_account(admin, username="amara", password="amara-pass-99", role="editor",
                   display_name="Amara O.")
    client, _ = sign_in(db_path, "amara", "amara-pass-99")
    assert is_refusal(client.get("/admin/users"))


def test_the_password_is_stored_hashed_and_never_echoed(client_as, db_path, caplog):
    admin = client_as("admin")
    with caplog.at_level(logging.DEBUG):
        response = post_to(admin, "/admin/users", username="amara",
                           password=NEW_PASSWORD, role="editor", display_name="Amara O.")
        user_id = int(re.search(r"/admin/users/(\d+)", response.headers["location"]).group(1))
        pages = [response.text, admin.get(response.headers["location"]).text,
                 admin.get("/admin/users").text, account_page(admin, user_id)]
    assert all(NEW_PASSWORD not in page for page in pages)
    assert NEW_PASSWORD not in caplog.text
    with sqlite3.connect(db_path) as conn:
        stored = conn.execute("SELECT password_hash FROM users WHERE username = 'amara'"
                              ).fetchone()[0]
    assert stored != NEW_PASSWORD and NEW_PASSWORD not in stored
    assert stored.startswith("$argon2")


def test_a_username_already_in_use_is_refused_without_a_second_account(client_as):
    admin = client_as("admin")
    create_account(admin, username="amara", display_name="Amara O.")
    response = post_to(admin, "/admin/users", username="AMARA", password="other-pass-12",
                       role="editor", display_name="Impostor")
    assert response.status_code == 409
    assert "already exists" in response.text
    assert "Impostor" not in admin.get("/admin/users").text


@pytest.mark.parametrize("changes,message", [
    ({"password": "short"}, "password"),
    ({"display_name": "   "}, "display name"),
    ({"username": "  "}, "username"),
    ({"role": "owner"}, "role"),
])
def test_an_account_form_with_a_problem_is_refused_and_keeps_what_was_typed(
        client_as, changes, message):
    admin = client_as("admin")
    form = {"username": "amara", "password": "amara-pass-99", "role": "editor",
            "display_name": "Amara O."} | changes
    response = post_to(admin, "/admin/users", **form)
    assert response.status_code == 400
    assert message in response.text.lower()
    assert "amara-pass-99" not in response.text
    assert 'value="short"' not in response.text
    assert "Amara O." not in admin.get("/admin/users").text


def test_the_create_form_never_prefills_a_password_after_an_error(client_as):
    admin = client_as("admin")
    response = post_to(admin, "/admin/users", username="amara", password="tiny",
                       role="editor", display_name="Amara O.")
    assert response.status_code == 400
    assert 'value="amara"' in response.text and 'value="Amara O."' in response.text
    assert 'value="tiny"' not in response.text


# -- roles -------------------------------------------------------------------

def test_admin_can_promote_an_editor_to_admin_and_back(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    assert post_to(admin, f"/admin/users/{user_id}/role", role="admin").status_code == 303
    assert shown(account_page(admin, user_id), "role") == "Admin"
    amara, _ = sign_in(db_path, "amara", "amara-pass-99")
    assert amara.get("/admin/users").status_code == 200

    assert post_to(admin, f"/admin/users/{user_id}/role", role="editor").status_code == 303
    assert shown(account_page(admin, user_id), "role") == "Editor"
    # the next request already uses the new role: no sign-out needed
    assert is_refusal(amara.get("/admin/users"))


def test_a_role_must_be_admin_or_editor(client_as):
    admin = client_as("admin")
    user_id = create_account(admin)
    assert post_to(admin, f"/admin/users/{user_id}/role", role="owner").status_code == 400
    assert shown(account_page(admin, user_id), "role") == "Editor"


def test_the_last_active_admin_cannot_be_demoted(client_as, db_path):
    admin = client_as("admin")
    admin_id = user_id_of(db_path, "admin")
    response = post_to(admin, f"/admin/users/{admin_id}/role", role="editor")
    assert response.status_code == 409
    assert "last" in response.text.lower()
    assert shown(account_page(admin, admin_id), "role") == "Admin"


def test_an_admin_can_step_down_when_another_active_admin_exists(client_as, db_path):
    admin = client_as("admin")
    create_account(admin, username="second", password="second-pass-1", role="admin",
                   display_name="Second Leader")
    admin_id = user_id_of(db_path, "admin")
    assert post_to(admin, f"/admin/users/{admin_id}/role", role="editor").status_code == 303


def test_a_deactivated_admin_does_not_count_as_another_admin(client_as, db_path):
    admin = client_as("admin")
    second = create_account(admin, username="second", password="second-pass-1",
                            role="admin", display_name="Second Leader")
    assert post_to(admin, f"/admin/users/{second}/deactivate").status_code == 303
    admin_id = user_id_of(db_path, "admin")
    assert post_to(admin, f"/admin/users/{admin_id}/role", role="editor").status_code == 409


# -- deactivating and reactivating ------------------------------------------

def test_deactivation_stops_sign_in_and_ends_an_existing_session(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    amara, _ = sign_in(db_path, "amara", "amara-pass-99")
    assert amara.get("/admin/posts").status_code == 200

    assert post_to(admin, f"/admin/users/{user_id}/deactivate").status_code == 303
    assert shown(account_page(admin, user_id), "status") == "Deactivated"

    stale = amara.get("/admin/posts", follow_redirects=False)       # the old session
    assert stale.status_code in (302, 303) and stale.headers["location"] == "/login"
    sent = post_to(amara, "/admin/posts", title="Sneaked in", body="y")
    assert sent.status_code in (302, 303) and sent.headers["location"] == "/login"
    assert "Sneaked in" not in admin.get("/admin/posts").text    # and it changed nothing
    fresh, response = sign_in(db_path, "amara", "amara-pass-99")
    assert response.status_code == 401
    assert "Incorrect username or password" in response.text


def test_reactivation_restores_sign_in(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    post_to(admin, f"/admin/users/{user_id}/deactivate")
    assert not can_sign_in(db_path, "amara", "amara-pass-99")
    assert post_to(admin, f"/admin/users/{user_id}/reactivate").status_code == 303
    assert shown(account_page(admin, user_id), "status") == "Active"
    assert can_sign_in(db_path, "amara", "amara-pass-99")


def test_accounts_are_never_deleted(client_as):
    admin = client_as("admin")
    user_id = create_account(admin)
    html = account_page(admin, user_id)
    assert "delete" not in html.lower()
    for path in (f"/admin/users/{user_id}/delete", f"/admin/users/{user_id}"):
        response = post_to(admin, path)
        assert response.status_code in (404, 405)
    assert shown(account_page(admin, user_id), "status") == "Active"


def test_an_admin_cannot_deactivate_their_own_account(client_as, db_path):
    admin = client_as("admin")
    admin_id = user_id_of(db_path, "admin")
    response = post_to(admin, f"/admin/users/{admin_id}/deactivate")
    assert response.status_code == 409
    assert shown(account_page(admin, admin_id), "status") == "Active"
    assert admin.get("/admin").status_code == 200


def test_deactivating_or_reactivating_a_missing_account_is_not_found(client_as):
    admin = client_as("admin")
    for action in ("deactivate", "reactivate", "role", "password", "display-name"):
        assert post_to(admin, f"/admin/users/9999/{action}", role="editor",
                       password="long-enough-pw", display_name="x").status_code == 404
    assert admin.get("/admin/users/9999").status_code == 404


# -- posts and bylines after changes ----------------------------------------

def test_a_deactivated_accounts_posts_stay_published_with_the_author_kept(
        client_as, db_path, tmp_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="newbie-pass-1",
                             display_name="Amara O.")
    post_id = author_post(db_path, "amara")
    post_to(admin, f"/admin/users/{user_id}/deactivate")

    html = admin.get(f"/admin/posts/{post_id}/edit").text
    assert re.search(r'id="post-status"[^>]*>\s*Published', html)
    assert "Amara O." in html                                  # the Author link is kept
    out = render_site(tmp_path / "site", database=db_path)
    assert "Afrobeat Night" in (out / "posts/afrobeat-night.html").read_text()


def test_a_display_name_change_shows_on_the_next_publish(client_as, db_path, tmp_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="newbie-pass-1",
                             display_name="Amara O.")
    post_id = author_post(db_path, "amara")
    page = lambda: (render_site(tmp_path / "site", database=db_path)
                    / "posts/afrobeat-night.html").read_text()
    assert "Amara O." in page()

    response = post_to(admin, f"/admin/users/{user_id}/display-name",
                       display_name="ASA Events Team")
    assert response.status_code == 303
    assert shown(account_page(admin, user_id), "display-name") == "ASA Events Team"
    updated = page()
    assert "ASA Events Team" in updated and "Amara O." not in updated
    # the Post is still hers: same Post, same slug, still Published
    html = admin.get(f"/admin/posts/{post_id}/edit").text
    assert "ASA Events Team" in html
    assert re.search(r'id="post-slug"[^>]*>\s*afrobeat-night', html)


def test_the_username_is_never_used_as_a_byline(client_as, db_path, tmp_path):
    admin = client_as("admin")
    create_account(admin, username="amara.private", password="newbie-pass-1",
                   display_name="Amara O.")
    author_post(db_path, "amara.private")
    out = render_site(tmp_path / "site", database=db_path)
    assert all("amara.private" not in p.read_text()
               for p in out.rglob("*") if p.suffix in (".html", ".css"))


def test_a_display_name_is_required(client_as):
    admin = client_as("admin")
    user_id = create_account(admin)
    response = post_to(admin, f"/admin/users/{user_id}/display-name", display_name="  ")
    assert response.status_code == 400
    assert shown(account_page(admin, user_id), "display-name") == "New Member"


# -- password reset ----------------------------------------------------------

def test_admin_sets_a_new_password_without_seeing_the_old_one(client_as, db_path, caplog):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    before = account_page(admin, user_id)
    assert "amara-pass-99" not in before and "argon2" not in before

    with sqlite3.connect(db_path) as conn:
        old_hash = conn.execute("SELECT password_hash FROM users WHERE username='amara'"
                                ).fetchone()[0]
    with caplog.at_level(logging.DEBUG):
        response = post_to(admin, f"/admin/users/{user_id}/password",
                           password=RESET_PASSWORD)
        assert response.status_code == 303
        pages = [response.text, admin.get(response.headers["location"]).text,
                 account_page(admin, user_id), admin.get("/admin/users").text]
    assert all(RESET_PASSWORD not in page and "amara-pass-99" not in page for page in pages)
    assert RESET_PASSWORD not in caplog.text

    assert can_sign_in(db_path, "amara", RESET_PASSWORD)
    assert not can_sign_in(db_path, "amara", "amara-pass-99")
    with sqlite3.connect(db_path) as conn:
        new_hash = conn.execute("SELECT password_hash FROM users WHERE username='amara'"
                                ).fetchone()[0]
    assert new_hash != old_hash and new_hash.startswith("$argon2")
    assert RESET_PASSWORD not in new_hash


def test_a_reset_password_that_is_too_short_is_refused_and_not_echoed(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    response = post_to(admin, f"/admin/users/{user_id}/password", password="tiny-pw")
    assert response.status_code == 400
    assert "password" in response.text.lower()
    assert "tiny-pw" not in response.text
    assert can_sign_in(db_path, "amara", "amara-pass-99")


def test_resetting_a_password_does_not_reactivate_a_deactivated_account(client_as, db_path):
    admin = client_as("admin")
    user_id = create_account(admin, username="amara", password="amara-pass-99",
                             display_name="Amara O.")
    post_to(admin, f"/admin/users/{user_id}/deactivate")
    assert post_to(admin, f"/admin/users/{user_id}/password",
                   password=RESET_PASSWORD).status_code == 303
    assert not can_sign_in(db_path, "amara", RESET_PASSWORD)
    post_to(admin, f"/admin/users/{user_id}/reactivate")
    assert can_sign_in(db_path, "amara", RESET_PASSWORD)


# -- the Editor is refused on every user-management screen and action -------

ACTIONS = [
    ("get", "/admin/users", None),
    ("get", "/admin/users/new", None),
    ("get", "/admin/users/{id}", None),
    ("post", "/admin/users", {"username": "intruder", "password": "intruder-pass-1",
                              "role": "admin", "display_name": "Intruder"}),
    ("post", "/admin/users/{id}/role", {"role": "admin"}),
    ("post", "/admin/users/{id}/deactivate", {}),
    ("post", "/admin/users/{id}/reactivate", {}),
    ("post", "/admin/users/{id}/password", {"password": "hijacked-pass-1"}),
    ("post", "/admin/users/{id}/display-name", {"display_name": "Hijacked"}),
]


@pytest.mark.parametrize("method,path,data", ACTIONS)
def test_editor_is_refused_every_account_screen_and_action(
        client_as, db_path, method, path, data):
    editor = client_as("editor")
    target = user_id_of(db_path, "admin")
    path = path.format(id=target)
    response = post_to(editor, path, **data) if method == "post" else editor.get(path)
    assert is_refusal(response)
    assert 'href="/admin"' in response.text          # the way back to the dashboard

    # nothing changed
    admin = client_as("admin")
    html = account_page(admin, target)
    assert shown(html, "role") == "Admin" and shown(html, "status") == "Active"
    assert shown(html, "display-name") == "ASA Leadership"
    assert "intruder" not in admin.get("/admin/users").text.lower()
    assert can_sign_in(db_path, "admin", DEMO_USERS["admin"]["password"])
    assert not can_sign_in(db_path, "admin", "hijacked-pass-1")


@pytest.mark.parametrize("method,path,data", ACTIONS)
def test_editor_is_refused_even_for_an_account_that_does_not_exist(
        client_as, method, path, data):
    editor = client_as("editor")
    path = path.format(id=9999)
    response = post_to(editor, path, **data) if method == "post" else editor.get(path)
    assert is_refusal(response)                       # permission comes before the lookup


def test_an_editor_cannot_change_their_own_role_or_display_name(client_as, db_path):
    editor = client_as("editor")
    me = user_id_of(db_path, "editor")
    assert is_refusal(post_to(editor, f"/admin/users/{me}/role", role="admin"))
    assert is_refusal(post_to(editor, f"/admin/users/{me}/display-name",
                              display_name="Boss"))
    assert is_refusal(post_to(editor, f"/admin/users/{me}/password",
                              password="my-own-new-pw-1"))
    assert can_sign_in(db_path, "editor", DEMO_USERS["editor"]["password"])
    assert is_refusal(editor.get("/admin/users"))


def test_user_management_is_hidden_from_an_editors_screens(client_as):
    admin, editor = client_as("admin"), client_as("editor")
    assert "/admin/users" in admin.get("/admin").text
    assert "/admin/users" not in editor.get("/admin").text
    assert "/admin/users" not in editor.get("/admin/posts").text


@pytest.mark.parametrize("method,path,data", ACTIONS)
def test_signed_out_visitors_are_sent_to_sign_in(client, method, path, data):
    response = getattr(client, method)(path.format(id=1), follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


def test_admin_is_not_refused_any_account_screen(client_as, db_path):
    admin = client_as("admin")
    target = create_account(admin)
    for path in ("/admin/users", "/admin/users/new", f"/admin/users/{target}"):
        assert admin.get(path).status_code == 200


# -- CSRF --------------------------------------------------------------------

def test_an_account_form_without_a_token_is_rejected_and_changes_nothing(client_as, db_path):
    admin = client_as("admin")
    target = create_account(admin)
    for path, data in [
        ("/admin/users", {"username": "sneaky", "password": "sneaky-pass-1",
                          "role": "admin", "display_name": "Sneaky"}),
        (f"/admin/users/{target}/role", {"role": "admin"}),
        (f"/admin/users/{target}/deactivate", {}),
        (f"/admin/users/{target}/reactivate", {}),
        (f"/admin/users/{target}/password", {"password": "forged-pass-123"}),
        (f"/admin/users/{target}/display-name", {"display_name": "Forged"}),
    ]:
        assert admin.post(path, data=data, follow_redirects=False).status_code == 403, path
        assert admin.post(path, data=data | {"csrf_token": "nope"},
                          follow_redirects=False).status_code == 403, path
    html = account_page(admin, target)
    assert shown(html, "role") == "Editor" and shown(html, "status") == "Active"
    assert shown(html, "display-name") == "New Member"
    assert "Sneaky" not in admin.get("/admin/users").text
    assert not can_sign_in(db_path, "newbie", "forged-pass-123")


def test_every_account_form_carries_a_csrf_token(client_as):
    admin = client_as("admin")
    target = create_account(admin)
    for path in ("/admin/users", "/admin/users/new", f"/admin/users/{target}"):
        html = admin.get(path).text
        for form in re.findall(r"<form\b[^>]*method=\"post\"[^>]*>.*?</form>", html, re.S):
            assert token_in(form), f"a form on {path} has no CSRF token"
    assert "<form" in admin.get("/admin/users/new").text
    assert admin.get(f"/admin/users/{target}").text.count("<form") >= 4


def test_account_form_actions_point_at_the_nested_routes(client_as):
    admin = client_as("admin")
    target = create_account(admin)
    base = f"/admin/users/{target}"
    actions = re.findall(r'<form [^>]*action="([^"]*)"', account_page(admin, target))
    assert actions == [f"{base}/display-name", f"{base}/role", f"{base}/password",
                       f"{base}/deactivate"]
    post_to(admin, f"{base}/deactivate")
    actions = re.findall(r'<form [^>]*action="([^"]*)"', account_page(admin, target))
    assert actions[-1] == f"{base}/reactivate"
