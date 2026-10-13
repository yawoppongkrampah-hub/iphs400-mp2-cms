"""T09: persistent admin navigation, and clear feedback after every action.

Seam 1 (the admin console over HTTP). What a signed-in person sees after they
act: a status message once, a clear error page instead of raw JSON, and the same
navigation on every admin screen.
"""
import re

import pytest

from tests.conftest import csrf_token
from tests.test_t03_publish import add_post
from tests.test_t05_pages import add_page

STATUS = re.compile(r'<p[^>]*role="status"[^>]*>(.*?)</p>', re.S)
NAV = re.compile(r'<nav[^>]*aria-label="Admin"[^>]*>(.*?)</nav>', re.S)
LINKS = re.compile(r'<a [^>]*href="([^"]*)"')


def status_text(html):
    match = STATUS.search(html)
    return " ".join(match.group(1).split()) if match else None


def post_to(client, path, **data):
    data["csrf_token"] = csrf_token(client, "/admin")
    return client.post(path, data=data, follow_redirects=True)


def nav_of(html):
    match = NAV.search(html)
    assert match, "no admin navigation on this screen"
    return match.group(1)


# -- the same navigation on every admin screen -------------------------------------

def screens(db_path):
    post_id = add_post(db_path, "Afrobeat Night", published=False)
    page_id = add_page(db_path, "Photos", "photos")
    return ["/admin", "/admin/content", "/admin/posts", "/admin/posts/new",
            f"/admin/posts/{post_id}/edit", "/admin/pages", f"/admin/pages/{page_id}/edit"]


EDITOR_NAV = ["/admin", "/admin/content", "/admin/posts", "/admin/pages"]
ADMIN_NAV = EDITOR_NAV + ["/admin/users"]
FORMS = re.compile(r'<form [^>]*action="([^"]*)"')


def test_the_navigation_is_exactly_the_same_set_for_a_role_on_every_screen(client_as, db_path):
    """The older tests set the navigation aside; this one holds it to an exact list per role."""
    urls = screens(db_path)
    for role, expected in (("editor", EDITOR_NAV), ("admin", ADMIN_NAV)):
        client = client_as(role)
        for url in urls + (["/admin/users", "/admin/users/new", "/admin/users/1"]
                           if role == "admin" else []):
            response = client.get(url)
            assert response.status_code == 200, url
            nav = nav_of(response.text)
            assert LINKS.findall(nav) == expected, (role, url)
            assert FORMS.findall(nav) == ["/logout"], (role, url)
            assert 'name="csrf_token"' in nav, (role, url)


def test_the_accounts_link_is_there_for_the_admin_and_never_for_an_editor(client_as, db_path):
    admin, editor = client_as("admin"), client_as("editor")
    for url in screens(db_path):
        assert 'href="/admin/users"' in nav_of(admin.get(url).text)
        assert "/admin/users" not in editor.get(url).text


def test_the_navigation_also_shows_on_the_refusal_page_and_the_preview(client_as):
    editor = client_as("editor")
    refused = editor.get("/admin/users")
    assert refused.status_code == 403
    preview = post_to(editor, "/admin/posts/preview", title="T", body="B")
    for page in (refused, preview):
        nav = nav_of(page.text)
        assert LINKS.findall(nav) == EDITOR_NAV and FORMS.findall(nav) == ["/logout"]
        assert "/admin/users" not in page.text


def test_the_sign_in_page_has_no_navigation(client):
    assert NAV.search(client.get("/login").text) is None


def test_signing_out_from_the_navigation_works_from_any_screen(client_as, db_path):
    client = client_as("editor")
    response = post_to(client, "/logout")
    assert 'name="password"' in response.text
    assert client.get("/admin", follow_redirects=False).status_code == 303


# -- success is said once ----------------------------------------------------------------

def test_signing_out_says_so_on_the_sign_in_page(client_as):
    assert "signed out" in status_text(post_to(client_as("editor"), "/logout").text).lower()


def test_a_message_is_shown_once_not_on_every_later_screen(client_as):
    client = client_as("editor")
    saved = post_to(client, "/admin/posts", title="Afrobeat Night", body="Body")
    assert status_text(saved.text)
    assert status_text(client.get("/admin/posts").text) is None


def test_post_actions_each_say_what_happened(client_as, db_path):
    editor = client_as("editor")
    created = post_to(editor, "/admin/posts", title="Afrobeat Night", body="Body")
    post_id = int(re.search(r"/admin/posts/(\d+)/edit", str(created.url)).group(1))
    assert "draft" in status_text(created.text).lower()

    saved = post_to(editor, f"/admin/posts/{post_id}", title="Afrobeat Night", body="New body")
    assert "saved" in status_text(saved.text).lower()

    published = post_to(editor, f"/admin/posts/{post_id}/publish")
    message = status_text(published.text).lower()
    assert "published" in message and "not live" in message      # Published is not Live

    unpublished = post_to(editor, f"/admin/posts/{post_id}/unpublish")
    assert "draft" in status_text(unpublished.text).lower()


def test_admin_post_actions_slug_and_delete_say_what_happened(client_as, db_path):
    admin = client_as("admin")
    post_id = add_post(db_path, "Afrobeat Night", published=False)
    slug = post_to(admin, f"/admin/posts/{post_id}/slug", slug="new-link")
    assert "slug" in status_text(slug.text).lower()
    deleted = post_to(admin, f"/admin/posts/{post_id}/delete")
    assert "deleted" in status_text(deleted.text).lower()
    assert str(deleted.url).endswith("/admin/posts")


def test_page_actions_each_say_what_happened(client_as, db_path):
    admin = client_as("admin")
    created = post_to(admin, "/admin/pages", title="Zeta", slug="zeta", body="Body")
    page_id = int(re.search(r"/admin/pages/(\d+)/edit", str(created.url)).group(1))
    assert "created" in status_text(created.text).lower()
    steps = [
        (f"/admin/pages/{page_id}", {"body": "More"}, "saved"),
        (f"/admin/pages/{page_id}/title", {"title": "Zeta Two"}, "title"),
        (f"/admin/pages/{page_id}/slug", {"slug": "zeta-two"}, "slug"),
        (f"/admin/pages/{page_id}/publish", {}, "published"),
        (f"/admin/pages/{page_id}/unpublish", {}, "draft"),
        (f"/admin/pages/{page_id}/delete", {}, "deleted"),
    ]
    for path, data, word in steps:
        assert word in status_text(post_to(admin, path, **data).text).lower(), path


def test_an_editor_saving_a_page_body_sees_that_it_saved(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    saved = post_to(client_as("editor"), f"/admin/pages/{page_id}", body="Fresh words")
    assert "saved" in status_text(saved.text).lower()


def test_account_actions_each_say_what_happened(client_as, db_path):
    admin = client_as("admin")
    created = post_to(admin, "/admin/users", username="newbie", password="newbie-password-1",
                      role="editor", display_name="New Person")
    user_id = int(re.search(r"/admin/users/(\d+)", str(created.url)).group(1))
    assert "created" in status_text(created.text).lower()
    steps = [
        (f"/admin/users/{user_id}/role", {"role": "admin"}, "role"),
        (f"/admin/users/{user_id}/display-name", {"display_name": "ASA Events Team"}, "display name"),
        (f"/admin/users/{user_id}/password", {"password": "brand-new-passphrase-9"}, "password"),
        (f"/admin/users/{user_id}/deactivate", {}, "deactivated"),
        (f"/admin/users/{user_id}/reactivate", {}, "reactivated"),
    ]
    for path, data, word in steps:
        message = status_text(post_to(admin, path, **data).text).lower()
        assert word in message, (path, message)


def test_a_password_reset_message_never_contains_the_password(client_as, db_path):
    admin = client_as("admin")
    response = post_to(admin, "/admin/users/2/password", password="never-show-this-passphrase")
    assert status_text(response.text)
    assert "never-show-this-passphrase" not in response.text


# -- failure is said clearly ------------------------------------------------------------

def test_a_failed_save_says_why_and_keeps_the_text(client_as):
    response = post_to(client_as("editor"), "/admin/posts", title="", body="Keep these words")
    assert response.status_code == 400
    assert 'role="alert"' in response.text and "Keep these words" in response.text


def test_a_missing_token_is_a_readable_page_not_raw_json(client_as):
    client = client_as("editor")
    response = client.post("/admin/posts", data={"title": "T", "body": "B"})
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("text/html")
    assert "token" in response.text.lower() and 'href="/admin"' in response.text


def test_a_missing_item_is_a_readable_page_with_a_way_back(client_as):
    response = client_as("editor").get("/admin/posts/9999/edit")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "no such post" in response.text.lower() and 'href="/admin/posts"' in nav_of(response.text)


def test_a_missing_token_at_sign_in_is_a_readable_page(client):
    response = client.post("/login", data={"username": "admin", "password": "x"})
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("text/html")
    assert 'href="/login"' in response.text


def test_the_same_failure_for_a_missing_page_account(client_as):
    admin = client_as("admin")
    for url, text in (("/admin/pages/9999/edit", "no such page"),
                      ("/admin/users/9999", "no such account")):
        response = admin.get(url)
        assert response.status_code == 404 and text in response.text.lower()
