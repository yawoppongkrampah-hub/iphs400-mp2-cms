"""T08: Preview and the Event details hint.

Seam 1 (the admin console over HTTP) for the editor screens, with one look at
Seam 2 (the published site on disk) to prove the Preview shows what goes Live.
"""
import re

import pytest

from app import pages, posts
from tests.conftest import csrf_token
from tests.test_t03_publish import add_post, author_id, publish, read
from tests.test_t05_pages import add_page, is_refusal

# Everything an Editor's Body could try, as one Body. The image is the one allowed thing.
ATTACK_BODY = (
    "## Details\n\n"
    "- **What:** a party\n\n"
    '<script>alert("pwned")</script>\n\n'
    '<iframe src="https://example.com/frame"></iframe>\n\n'
    '<form action="/admin/posts/1/delete" method="post"><button>Delete</button></form>\n\n'
    '<p onclick="steal()">Click <img src="x" onerror="steal()"></p>\n\n'
    "[Manage users](/admin/users)\n\n"
    "![Three red circles](images/demo-illustration-1.svg)\n"
)

BODY_FRAGMENT = re.compile(r'<div class="body">(.*?)</div>', re.S)


def body_html(html):
    """The rendered Body of a page: the same wrapper on Preview and on the public site."""
    match = BODY_FRAGMENT.search(html)
    assert match, "no rendered Body in the page"
    return match.group(1)


def post_to(client, path, **data):
    data["csrf_token"] = csrf_token(client, "/admin")
    return client.post(path, data=data, follow_redirects=False)


def preview_post(client, title="Afrobeat Night", body=ATTACK_BODY, **extra):
    return post_to(client, "/admin/posts/preview", title=title, body=body, **extra)


def preview_page(client, page_id, body=ATTACK_BODY, **extra):
    return post_to(client, f"/admin/pages/{page_id}/preview", body=body, **extra)


def textarea_body(html):
    import html as htmllib
    return htmllib.unescape(re.search(r'<textarea[^>]*name="body"[^>]*>(.*?)</textarea>',
                                      html, re.S).group(1))


# -- Preview matches the published site ---------------------------------------

@pytest.mark.parametrize("role", ["editor", "admin"])
def test_post_preview_body_is_what_the_published_post_renders(role, client_as, db_path, tmp_path):
    add_post(db_path, "Afrobeat Night", ATTACK_BODY)
    live = body_html(read(publish(db_path, tmp_path), "posts/afrobeat-night.html"))

    response = preview_post(client_as(role))

    assert response.status_code == 200
    assert body_html(response.text) == live
    assert 'alt="Three red circles"' in live


@pytest.mark.parametrize("role", ["editor", "admin"])
def test_page_preview_body_is_what_the_published_page_renders(role, client_as, db_path, tmp_path):
    page_id = add_page(db_path, "Photos", "photos", ATTACK_BODY)
    live = body_html(read(publish(db_path, tmp_path), "photos.html"))

    response = preview_page(client_as(role), page_id)

    assert response.status_code == 200
    assert body_html(response.text) == live
    assert 'alt="Three red circles"' in live


def test_preview_shows_the_title_and_uses_the_unsaved_text(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos", "Old saved text")
    editor = client_as("editor")

    post_preview = preview_post(editor, title="Unsaved Title", body="Fresh **words**")
    page_preview = preview_page(editor, page_id, body="Fresh **words**")

    assert "Unsaved Title" in post_preview.text
    assert "<strong>words</strong>" in post_preview.text
    assert "<strong>words</strong>" in page_preview.text
    assert "Old saved text" not in page_preview.text
    assert "Photos" in page_preview.text                        # the Page's own title
    assert pages.get(db_path, page_id)["body"] == "Old saved text"      # nothing was saved


def test_preview_does_not_run_raw_html(client_as):
    html = body_html(preview_post(client_as("editor")).text)
    for forbidden in ("<script", "<iframe", "<form", "onclick", "onerror", "alert("):
        assert forbidden not in html
    assert 'href="/admin/users"' not in html           # root-absolute links are dropped


def test_preview_images_load_from_the_approved_images_folder(client_as):
    editor = client_as("editor")
    page = preview_post(editor, body="![Three red circles](images/demo-illustration-1.svg)")
    src = re.search(r'<img[^>]*src="([^"]+)"', page.text).group(1)
    base = re.search(r'<base href="([^"]+)"', page.text).group(1)
    assert base.startswith("/admin/")                  # the console serves the image, not the site

    image = editor.get("/admin/preview/images/demo-illustration-1.svg")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/svg")
    assert src == "../images/demo-illustration-1.svg"      # the same src the public Post has


def test_preview_image_route_refuses_anything_outside_the_images_folder(client_as):
    editor = client_as("editor")
    for path in ("../../.env", "..%2f..%2f.env", "%2e%2e/%2e%2e/pyproject.toml",
                 "README.md", "nothing-here.png"):
        assert editor.get(f"/admin/preview/images/{path}").status_code in (400, 404)


# -- Preview cannot be a way into Admin-only actions -----------------------------

def test_an_editors_preview_offers_no_admin_only_control(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    editor = client_as("editor")
    for response in (preview_post(editor), preview_page(editor, page_id)):
        assert response.status_code == 200
        assert "<form" not in response.text and "<button" not in response.text
        for admin_only in ("/admin/users", "/delete", "/slug", '/title"', "/unpublish",
                           "Delete this", "Change the slug", "Mark Published"):
            assert admin_only not in response.text


def test_preview_ignores_fields_that_would_change_something(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos", "Saved", published=False)
    post_id = add_post(db_path, "Afrobeat Night", "Saved", published=False)
    editor = client_as("editor")

    preview_page(editor, page_id, title="Hacked", slug="hacked", status="published")
    preview_post(editor, title="Afrobeat Night", slug="hacked", status="published",
                 post_id=str(post_id))

    page = pages.get(db_path, page_id)
    assert (page["title"], page["slug"], page["status"], page["body"]) == (
        "Photos", "photos", "draft", "Saved")
    post = posts.get(db_path, post_id)
    assert (post["slug"], post["status"], post["body"]) == ("afrobeat-night", "draft", "Saved")


def test_preview_needs_a_csrf_token(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    editor = client_as("editor")
    assert editor.post("/admin/posts/preview", data={"title": "T", "body": "B"}).status_code == 403
    assert editor.post(f"/admin/pages/{page_id}/preview", data={"body": "B"}).status_code == 403


def test_preview_sends_a_signed_out_visitor_to_sign_in(client, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    for path in ("/admin/posts/preview", f"/admin/pages/{page_id}/preview"):
        response = client.post(path, data={"title": "T", "body": "B"}, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/login"
    assert client.get("/admin/preview/images/demo-illustration-1.svg",
                      follow_redirects=False).status_code == 303


def test_preview_of_a_missing_page_is_a_404_for_everyone_signed_in(client_as):
    assert preview_page(client_as("editor"), 9999).status_code == 404


# -- The Event details hint -----------------------------------------------------

def test_the_post_editor_shows_the_hint_but_never_puts_it_in_the_body(client_as, db_path):
    editor = client_as("editor")
    for html in (editor.get("/admin/posts/new").text,
                 editor.get(f"/admin/posts/{add_post(db_path, 'Afrobeat Night', 'My words')}/edit").text):
        hint = re.search(r'<aside[^>]*id="event-details-hint".*?</aside>', html, re.S)
        assert hint, "no Event details hint"
        for word in ("What", "When", "Where", "Who can attend"):
            assert word in hint.group(0)
        assert "What" not in textarea_body(html)
        assert "Who can attend" not in textarea_body(html)


def test_the_page_editor_has_no_event_details_hint(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    assert "event-details-hint" not in client_as("editor").get(f"/admin/pages/{page_id}/edit").text


def test_hiding_the_hint_leaves_the_body_unchanged(client_as, db_path):
    post_id = add_post(db_path, "Afrobeat Night", "My own words", published=False)
    editor = client_as("editor")
    before = editor.get(f"/admin/posts/{post_id}/edit").text
    assert "event-details-hint" in before

    hidden = post_to(editor, "/admin/posts/hint", action="hide", post_id=str(post_id),
                     title="Afrobeat Night", body="My own words")
    assert hidden.status_code == 200 and "event-details-hint" not in hidden.text

    after = editor.get(f"/admin/posts/{post_id}/edit").text
    assert "event-details-hint" not in after            # stays hidden on the next visit
    assert textarea_body(after) == textarea_body(before) == "My own words"
    assert posts.get(db_path, post_id)["body"] == "My own words"
    assert "event-details-hint" not in editor.get("/admin/posts/new").text


def test_hiding_the_hint_keeps_text_typed_but_not_yet_saved(client_as, db_path):
    post_id = add_post(db_path, "Afrobeat Night", "Saved words", published=False)
    editor = client_as("editor")

    hidden = post_to(editor, "/admin/posts/hint", action="hide", post_id=str(post_id),
                     title="Edited title", body="Unsaved words")

    assert textarea_body(hidden.text) == "Unsaved words"
    assert 'value="Edited title"' in hidden.text
    saved = posts.get(db_path, post_id)
    assert (saved["title"], saved["body"]) == ("Afrobeat Night", "Saved words")


def test_the_hint_can_be_shown_again(client_as):
    editor = client_as("editor")
    post_to(editor, "/admin/posts/hint", action="hide", title="", body="")
    assert "event-details-hint" not in editor.get("/admin/posts/new").text
    shown = post_to(editor, "/admin/posts/hint", action="show", title="", body="")
    assert "event-details-hint" in shown.text
    assert "event-details-hint" in editor.get("/admin/posts/new").text


def test_the_hint_choice_belongs_to_one_session(client_as):
    editor, admin = client_as("editor"), client_as("admin")
    post_to(editor, "/admin/posts/hint", action="hide", title="", body="")
    assert "event-details-hint" in admin.get("/admin/posts/new").text


def test_hint_route_needs_a_csrf_token_and_a_session(client, client_as):
    data = {"action": "hide", "title": "", "body": ""}
    assert client_as("editor").post("/admin/posts/hint", data=data).status_code == 403
    assert client.post("/admin/posts/hint", data=data,
                       follow_redirects=False).headers["location"] == "/login"


# -- the editors link to Preview ------------------------------------------------

def test_both_editors_have_a_preview_button_that_opens_in_a_new_tab(client_as, db_path):
    page_id = add_page(db_path, "Photos", "photos")
    editor = client_as("editor")
    post_form = editor.get("/admin/posts/new").text
    page_form = editor.get(f"/admin/pages/{page_id}/edit").text
    assert 'formaction="/admin/posts/preview"' in post_form
    assert f'formaction="/admin/pages/{page_id}/preview"' in page_form
    for html in (post_form, page_form):
        assert 'formtarget="_blank"' in html


def test_a_refusal_is_still_a_refusal(client_as):
    # Preview is for Editors too, but it must not have loosened an Admin-only rule.
    assert is_refusal(post_to(client_as("editor"), "/admin/users", username="x"))


def test_a_hint_request_with_a_strange_post_id_is_not_a_server_error(client_as):
    editor = client_as("editor")
    for post_id in ("²", "-1", "1e3", "abc"):
        response = post_to(editor, "/admin/posts/hint", action="hide", post_id=post_id,
                           title="", body="")
        assert response.status_code in (200, 404), post_id


def test_the_approved_image_rule_refuses_paths_that_leave_the_folder():
    from app import settings
    from app.publish import is_approved_image
    assert is_approved_image(settings.IMAGES, settings.IMAGES / "demo-illustration-1.svg")
    for outside in ("../pyproject.toml", "../.env.example", "../README.md",
                    "../images/../.env", "/etc/hosts"):
        assert not is_approved_image(settings.IMAGES, settings.IMAGES / outside)


def test_a_directly_opened_preview_image_is_sandboxed(client_as):
    response = client_as("editor").get("/admin/preview/images/demo-illustration-1.svg")
    assert response.headers["content-security-policy"] == "sandbox"
