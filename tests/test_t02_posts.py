"""T02: an Editor writes a Post, with roles and Permission refusal.

Seam 1 (the admin console over HTTP): everything here is what a signed-in
person sees and can do, or what the server answers to a request sent directly.
"""
import re
import time

import pytest

from tests.conftest import csrf_token, token_in

REFUSAL = "you don't have permission"


def create_post(client, title="Afrobeat Night", body="What: music", **kw):
    response = client.post(
        "/admin/posts",
        data={"title": title, "body": body,
              "csrf_token": csrf_token(client, "/admin/posts/new")},
        follow_redirects=False, **kw,
    )
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/posts/(\d+)/edit", response.headers["location"]).group(1))


def post_to(client, path, **data):
    data["csrf_token"] = csrf_token(client, "/admin/posts/new")
    return client.post(path, data=data, follow_redirects=False)


def edit_page(client, post_id):
    response = client.get(f"/admin/posts/{post_id}/edit")
    assert response.status_code == 200
    return response.text


def time_of(html, name):
    """The machine-readable time in <time id="name" datetime="...">, or None."""
    match = re.search(rf'<time id="{name}"[^>]*datetime="([^"]*)"', html)
    return match.group(1) if match else None


def slug_of(html):
    match = re.search(r'id="post-slug"[^>]*>([^<]+)<', html)
    assert match, "the slug is not shown"
    return match.group(1).strip()


def is_refusal(response):
    return response.status_code == 403 and REFUSAL in response.text.lower()


# -- writing, drafts, editing ----------------------------------------------

def test_editor_creates_a_draft_and_it_is_listed(client_as):
    editor = client_as("editor")
    post_id = create_post(editor, "Afrobeat Night", "What: music\n\nWhere: Gund")
    html = edit_page(editor, post_id)
    assert "Afrobeat Night" in html
    assert "What: music" in html
    assert "draft" in html.lower()
    assert "Afrobeat Night" in editor.get("/admin/posts").text


def test_author_is_the_signed_in_account_and_needs_no_form_field(client_as):
    editor = client_as("editor")
    assert 'name="author' not in editor.get("/admin/posts/new").text
    html = edit_page(editor, create_post(editor))
    assert "ASA Events Team" in html      # the editor's Display name
    assert "ASA Leadership" not in html


def test_posts_record_created_and_updated_times_automatically(client_as):
    editor = client_as("editor")
    html = edit_page(editor, create_post(editor))
    assert time_of(html, "created")
    assert time_of(html, "updated")


def test_editing_saves_the_new_title_and_body(client_as):
    editor = client_as("editor")
    post_id = create_post(editor, "Old title", "old body")
    before = time_of(edit_page(editor, post_id), "updated")
    time.sleep(0.01)
    response = post_to(editor, f"/admin/posts/{post_id}", title="New title", body="new body")
    assert response.status_code == 303
    html = edit_page(editor, post_id)
    assert "New title" in html and "new body" in html
    assert "Old title" not in html
    assert time_of(html, "updated") > before


def test_a_post_needs_a_title(client_as):
    editor = client_as("editor")
    response = post_to(editor, "/admin/posts", title="   ", body="text")
    assert response.status_code == 400
    assert "title" in response.text.lower()
    assert "text" in response.text            # what was typed is not lost


def test_editor_can_edit_a_post_written_by_someone_else(client_as):
    post_id = create_post(client_as("admin"), "Admin's post", "original")
    editor = client_as("editor")
    response = post_to(editor, f"/admin/posts/{post_id}", title="Corrected", body="fixed time")
    assert response.status_code == 303
    assert "fixed time" in edit_page(editor, post_id)
    # ...and the Author is still the person who wrote it.
    assert "ASA Leadership" in edit_page(editor, post_id)


def test_editing_a_missing_post_is_not_found(client_as):
    assert client_as("editor").get("/admin/posts/9999/edit").status_code == 404


# -- Draft / Published -----------------------------------------------------

def test_publish_and_unpublish_change_the_status(client_as):
    editor = client_as("editor")
    post_id = create_post(editor)
    assert "not yet published" in edit_page(editor, post_id).lower()

    assert post_to(editor, f"/admin/posts/{post_id}/publish").status_code == 303
    published = edit_page(editor, post_id)
    assert 'id="post-status"' in published
    assert re.search(r'id="post-status"[^>]*>\s*Published', published)

    assert post_to(editor, f"/admin/posts/{post_id}/unpublish").status_code == 303
    assert re.search(r'id="post-status"[^>]*>\s*Draft', edit_page(editor, post_id))


def test_first_published_date_is_set_once_and_kept(client_as):
    editor = client_as("editor")
    post_id = create_post(editor)
    assert time_of(edit_page(editor, post_id), "first-published") is None

    post_to(editor, f"/admin/posts/{post_id}/publish")
    first = time_of(edit_page(editor, post_id), "first-published")
    assert first

    post_to(editor, f"/admin/posts/{post_id}/unpublish")
    assert time_of(edit_page(editor, post_id), "first-published") == first

    time.sleep(0.01)
    post_to(editor, f"/admin/posts/{post_id}/publish")
    assert time_of(edit_page(editor, post_id), "first-published") == first


def test_publishing_twice_does_not_move_the_first_published_date(client_as):
    editor = client_as("editor")
    post_id = create_post(editor)
    post_to(editor, f"/admin/posts/{post_id}/publish")
    first = time_of(edit_page(editor, post_id), "first-published")
    time.sleep(0.01)
    post_to(editor, f"/admin/posts/{post_id}/publish")
    assert time_of(edit_page(editor, post_id), "first-published") == first


# -- slugs -----------------------------------------------------------------

def test_slug_is_generated_from_the_title(client_as):
    editor = client_as("editor")
    post_id = create_post(editor, "Afrobeat Night!  (Friday)")
    assert slug_of(edit_page(editor, post_id)) == "afrobeat-night-friday"


def test_a_number_is_added_when_the_slug_exists(client_as):
    editor = client_as("editor")
    slugs = [slug_of(edit_page(editor, create_post(editor, "Afrobeat Night")))
             for _ in range(3)]
    assert slugs == ["afrobeat-night", "afrobeat-night-2", "afrobeat-night-3"]


def test_a_title_with_no_letters_still_gets_a_slug(client_as):
    editor = client_as("editor")
    assert slug_of(edit_page(editor, create_post(editor, "!!!")))


def test_slug_does_not_change_when_the_title_is_edited(client_as):
    editor = client_as("editor")
    post_id = create_post(editor, "Afrobeat Night")
    post_to(editor, f"/admin/posts/{post_id}", title="Afrobeat Night (moved to Saturday)", body="x")
    assert slug_of(edit_page(editor, post_id)) == "afrobeat-night"


def test_slug_survives_publish_and_unpublish(client_as):
    editor = client_as("editor")
    post_id = create_post(editor, "Afrobeat Night")
    post_to(editor, f"/admin/posts/{post_id}/publish")
    post_to(editor, f"/admin/posts/{post_id}/unpublish")
    assert slug_of(edit_page(editor, post_id)) == "afrobeat-night"


def test_editors_never_enter_a_slug(client_as):
    editor = client_as("editor")
    assert "slug" not in editor.get("/admin/posts/new").text.lower()
    post_id = create_post(editor, "Real title")
    assert 'name="slug"' not in edit_page(editor, post_id)     # shown, but not editable
    # A slug smuggled into the ordinary forms is ignored.
    post_to(editor, "/admin/posts", title="Another", body="x", slug="hacked")
    post_to(editor, f"/admin/posts/{post_id}", title="Real title", body="x", slug="hacked")
    assert slug_of(edit_page(editor, post_id)) == "real-title"


def test_admin_can_change_a_slug_and_is_warned_first(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    html = edit_page(admin, post_id)
    assert "break" in html.lower() and "link" in html.lower()
    response = post_to(admin, f"/admin/posts/{post_id}/slug", slug="Afrobeat Friday")
    assert response.status_code == 303
    assert slug_of(edit_page(admin, post_id)) == "afrobeat-friday"


def test_admin_cannot_give_a_post_a_slug_that_is_taken(client_as):
    admin = client_as("admin")
    create_post(admin, "Afrobeat Night")
    other = create_post(admin, "Something else")
    response = post_to(admin, f"/admin/posts/{other}/slug", slug="afrobeat-night")
    assert response.status_code == 409
    assert slug_of(edit_page(admin, other)) == "something-else"


def test_admin_cannot_blank_a_slug(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    assert post_to(admin, f"/admin/posts/{post_id}/slug", slug="  !! ").status_code == 400
    assert slug_of(edit_page(admin, post_id)) == "afrobeat-night"


# -- delete ----------------------------------------------------------------

def test_admin_can_delete_a_post(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Mistake")
    assert post_to(admin, f"/admin/posts/{post_id}/delete").status_code == 303
    assert admin.get(f"/admin/posts/{post_id}/edit").status_code == 404
    assert "Mistake" not in admin.get("/admin/posts").text


# -- permissions: the Post part of the matrix ------------------------------

def test_admin_only_controls_are_hidden_from_an_editor(client_as):
    post_id = create_post(client_as("editor"), "Afrobeat Night")
    editor_html = edit_page(client_as("editor"), post_id)
    admin_html = edit_page(client_as("admin"), post_id)
    for control in (f"/admin/posts/{post_id}/delete", f"/admin/posts/{post_id}/slug"):
        assert control in admin_html
        assert control not in editor_html


ADMIN_ONLY = [
    ("post", "/admin/posts/{id}/delete", {}),
    ("post", "/admin/posts/{id}/slug", {"slug": "hacked"}),
    ("get", "/admin/posts/{id}/slug", None),
]


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY)
def test_editor_is_refused_every_admin_only_post_action(client_as, method, path, data):
    post_id = create_post(client_as("admin"), "Afrobeat Night")
    editor = client_as("editor")
    path = path.format(id=post_id)
    if method == "post":
        response = post_to(editor, path, **data)
    else:
        response = editor.get(path)
    assert is_refusal(response)
    # nothing changed: the Post still exists, with its own slug
    admin_html = edit_page(client_as("admin"), post_id)
    assert slug_of(admin_html) == "afrobeat-night"
    assert "Afrobeat Night" in client_as("admin").get("/admin/posts").text


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY)
def test_editor_is_refused_even_for_a_post_that_does_not_exist(client_as, method, path, data):
    editor = client_as("editor")
    path = path.format(id=9999)
    response = post_to(editor, path, **data) if method == "post" else editor.get(path)
    assert is_refusal(response)     # permission is checked before the lookup


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY)
def test_admin_is_not_refused_admin_only_actions(client_as, method, path, data):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    path = path.format(id=post_id)
    data = {"slug": "new-slug"} if data else data
    response = post_to(admin, path, **data) if method == "post" else admin.get(path)
    assert response.status_code in (200, 303)
    after = admin.get(f"/admin/posts/{post_id}/edit")
    if path.endswith("/delete"):
        assert after.status_code == 404
    elif method == "post":
        assert slug_of(after.text) == "new-slug"


def test_editor_can_do_every_editor_action(client_as):
    editor = client_as("editor")
    assert editor.get("/admin/posts").status_code == 200
    assert editor.get("/admin/posts/new").status_code == 200
    post_id = create_post(editor)
    assert editor.get(f"/admin/posts/{post_id}/edit").status_code == 200
    assert post_to(editor, f"/admin/posts/{post_id}", title="t", body="b").status_code == 303
    assert post_to(editor, f"/admin/posts/{post_id}/publish").status_code == 303
    assert post_to(editor, f"/admin/posts/{post_id}/unpublish").status_code == 303


def test_editor_can_publish_and_unpublish_a_post_written_by_someone_else(client_as):
    post_id = create_post(client_as("admin"), "Admin's post")
    editor = client_as("editor")
    assert post_to(editor, f"/admin/posts/{post_id}/publish").status_code == 303
    assert re.search(r'id="post-status"[^>]*>\s*Published', edit_page(editor, post_id))
    assert post_to(editor, f"/admin/posts/{post_id}/unpublish").status_code == 303
    assert re.search(r'id="post-status"[^>]*>\s*Draft', edit_page(editor, post_id))


def test_the_refusal_page_links_back_to_the_dashboard(client_as):
    post_id = create_post(client_as("admin"))
    response = post_to(client_as("editor"), f"/admin/posts/{post_id}/delete")
    assert is_refusal(response)
    assert 'href="/admin"' in response.text


# -- signed-out visitors ---------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/admin/posts"),
    ("get", "/admin/posts/new"),
    ("get", "/admin/posts/1/edit"),
    ("get", "/admin/posts/1/slug"),
    ("post", "/admin/posts"),
    ("post", "/admin/posts/1"),
    ("post", "/admin/posts/1/publish"),
    ("post", "/admin/posts/1/unpublish"),
    ("post", "/admin/posts/1/delete"),
    ("post", "/admin/posts/1/slug"),
])
def test_signed_out_visitors_are_sent_to_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


# -- CSRF ------------------------------------------------------------------

def test_a_post_form_without_a_token_is_rejected_and_changes_nothing(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Keep me")
    for path, data in [
        ("/admin/posts", {"title": "Sneaky", "body": "x"}),
        (f"/admin/posts/{post_id}", {"title": "Changed", "body": "x"}),
        (f"/admin/posts/{post_id}/publish", {}),
        (f"/admin/posts/{post_id}/unpublish", {}),
        (f"/admin/posts/{post_id}/slug", {"slug": "changed"}),
        (f"/admin/posts/{post_id}/delete", {}),
    ]:
        response = admin.post(path, data=data, follow_redirects=False)
        assert response.status_code == 403, path
    assert "Keep me" in edit_page(admin, post_id)
    assert "Sneaky" not in admin.get("/admin/posts").text
    assert slug_of(edit_page(admin, post_id)) == "keep-me"


def test_a_wrong_token_is_rejected(client_as):
    admin = client_as("admin")
    response = admin.post("/admin/posts", data={"title": "x", "body": "y", "csrf_token": "nope"})
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_every_post_form_carries_a_csrf_token(client_as, role):
    client = client_as(role)
    post_id = create_post(client)
    pages = ["/admin/posts/new", f"/admin/posts/{post_id}/edit", "/admin/posts"]
    if role == "admin":
        pages.append(f"/admin/posts/{post_id}/slug")
    for path in pages:
        html = client.get(path).text
        forms = re.findall(r"<form\b[^>]*method=\"post\"[^>]*>.*?</form>", html, re.S)
        for form in forms:
            assert token_in(form), f"a form on {path} has no CSRF token"
