"""T06: the Dashboard counts and the filterable Content list.

Seam 1 (the admin console over HTTP): what a signed-in person sees on the
Dashboard and in the Content list, for each role, after content changes.
"""
import re
import sqlite3

import pytest

from app import accounts, pages, posts
from tests.conftest import csrf_token
from tests.test_t03_publish import add_post, author_id
from tests.test_t05_pages import add_page, create_page
from tests.test_t05_pages import post_to as post_to_page

CONTENT = "/admin/content"
FOUR = ("published-posts", "draft-posts", "published-pages", "draft-pages")


def counts(html):
    """The four content counts as {name: int}, from id="count-<name>"."""
    found = {name: re.search(rf'id="count-{name}"[^>]*>\s*(\d+)\s*<', html) for name in FOUR}
    assert all(found.values()), f"a content count is missing: {found}"
    return {name: int(match.group(1)) for name, match in found.items()}


def account_counts(html):
    active = re.search(r'id="count-active-accounts"[^>]*>\s*(\d+)\s*<', html)
    deactivated = re.search(r'id="count-deactivated-accounts"[^>]*>\s*(\d+)\s*<', html)
    return (int(active.group(1)), int(deactivated.group(1))) if active and deactivated else None


def rows(html):
    """Each Content list row as a dict of what it shows."""
    result = []
    for block in re.findall(r'<li class="content-row".*?</li>', html, re.S):
        def field(name):
            match = re.search(rf'class="row-{name}"[^>]*>(.*?)</', block, re.S)
            return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else None
        updated = re.search(r'<time class="row-updated" datetime="([^"]*)"', block)
        result.append({"title": field("title"), "type": field("type"),
                       "status": field("status"), "author": field("author"),
                       "updated": updated.group(1) if updated else None,
                       "href": re.search(r'<a [^>]*href="([^"]*)"', block).group(1)})
    return result


def titles(html):
    return [row["title"] for row in rows(html)]


def listing(client, **query):
    response = client.get(CONTENT, params=query)
    assert response.status_code == 200, response.text
    return response.text


def add_account(db_path, username, display_name, role="editor"):
    return accounts.create_account(db_path, username=username, password="pass-word-99",
                                   role=role, display_name=display_name)


def seed_mix(db_path):
    """2 Published and 1 Draft Post; 1 Published and 2 Draft Pages."""
    add_post(db_path, "Afrobeat Night")
    add_post(db_path, "Movie Evening")
    add_post(db_path, "Draft Idea", published=False)
    add_page(db_path, "About ASA")
    add_page(db_path, "Resources", published=False)
    add_page(db_path, "Photos", published=False)


# == the Dashboard counts ======================================================

@pytest.mark.parametrize("role", ["admin", "editor"])
def test_every_signed_in_user_sees_the_four_content_counts(client_as, db_path, role):
    seed_mix(db_path)
    assert counts(client_as(role).get("/admin").text) == {
        "published-posts": 2, "draft-posts": 1, "published-pages": 1, "draft-pages": 2}


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_an_empty_site_shows_zero_not_nothing(client_as, role):
    assert counts(client_as(role).get("/admin").text) == dict.fromkeys(FOUR, 0)


def test_the_admin_also_sees_active_and_deactivated_account_counts(client_as, db_path):
    admin = client_as("admin")
    assert account_counts(admin.get("/admin").text) == (2, 0)
    add_account(db_path, "amara", "Amara O.")
    former = add_account(db_path, "kofi", "Kofi A.")
    accounts.deactivate(db_path, former, acting_user_id=author_id(db_path, "admin"))
    assert account_counts(admin.get("/admin").text) == (3, 1)


def test_an_editor_never_sees_account_numbers_anywhere(client_as, db_path):
    former = add_account(db_path, "kofi", "Kofi A.")
    accounts.deactivate(db_path, former, acting_user_id=author_id(db_path, "admin"))
    editor = client_as("editor")
    for url in ("/admin", CONTENT, f"{CONTENT}?type=post", f"{CONTENT}?status=draft"):
        html = editor.get(url).text
        assert account_counts(html) is None, url
        assert "count-active-accounts" not in html
        assert "count-deactivated-accounts" not in html
        assert "deactivated accounts" not in html.lower()
        assert "active accounts" not in html.lower()


def test_account_numbers_cannot_be_asked_for_by_a_direct_request(client_as):
    editor = client_as("editor")
    for url in ("/admin?counts=accounts", "/admin?role=admin", f"{CONTENT}?show=accounts",
                "/admin/counts", "/admin/accounts/count"):
        response = editor.get(url)
        assert account_counts(response.text) is None, url
        assert "deactivated" not in response.text.lower(), url


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_the_dashboard_reminds_that_published_is_not_live(client_as, role):
    html = client_as(role).get("/admin").text
    reminder = re.search(r'id="live-reminder"[^>]*>(.*?)</', html, re.S)
    assert reminder, "no Live reminder"
    text = re.sub(r"<[^>]+>", "", re.sub(r"\s+", " ", reminder.group(1))).lower()
    assert "published" in text and "live" in text
    assert "cms publish" in html and "cms deploy" in html
    assert "changes not live yet" not in html.lower()


def test_the_dashboard_counts_link_to_the_matching_filtered_list(client_as, db_path):
    seed_mix(db_path)
    admin = client_as("admin")
    html = admin.get("/admin").text
    for name, expected in (("published-posts", {"Afrobeat Night", "Movie Evening"}),
                           ("draft-pages", {"Resources", "Photos"})):
        block = re.search(rf'<a [^>]*href="([^"]*)"[^>]*>[^<]*<[^>]*id="count-{name}"', html)
        assert block, f"count-{name} is not a link"
        target = block.group(1).replace("&amp;", "&")
        assert set(titles(admin.get(target).text)) == expected


def test_the_dashboard_still_has_one_form_the_sign_out_button(client_as):
    assert len(re.findall(r"<form ", client_as("editor").get("/admin").text)) == 1


# == the Content list ==========================================================

def test_the_content_list_needs_sign_in(client):
    for url in (CONTENT, f"{CONTENT}?type=post&status=draft"):
        response = client.get(url, follow_redirects=False)
        assert response.status_code in (302, 303)
        assert response.headers["location"] == "/login"


@pytest.mark.parametrize("role", ["admin", "editor"])
def test_one_list_holds_both_posts_and_pages(client_as, db_path, role):
    seed_mix(db_path)
    html = listing(client_as(role))
    assert {row["type"] for row in rows(html)} == {"Post", "Page"}
    assert sorted(titles(html)) == sorted([
        "Afrobeat Night", "Movie Evening", "Draft Idea",
        "About ASA", "Resources", "Photos"])


@pytest.mark.parametrize("query, expected", [
    ({"type": "post"}, {"Afrobeat Night", "Movie Evening", "Draft Idea"}),
    ({"type": "page"}, {"About ASA", "Resources", "Photos"}),
    ({"status": "draft"}, {"Draft Idea", "Resources", "Photos"}),
    ({"status": "published"}, {"Afrobeat Night", "Movie Evening", "About ASA"}),
    ({"type": "post", "status": "published"}, {"Afrobeat Night", "Movie Evening"}),
    ({"type": "post", "status": "draft"}, {"Draft Idea"}),
    ({"type": "page", "status": "published"}, {"About ASA"}),
    ({"type": "page", "status": "draft"}, {"Resources", "Photos"}),
])
def test_each_filter_alone_and_together(client_as, db_path, query, expected):
    seed_mix(db_path)
    assert set(titles(listing(client_as("editor"), **query))) == expected


def test_a_filter_with_no_matches_says_so(client_as, db_path):
    add_post(db_path, "Afrobeat Night")
    html = listing(client_as("editor"), type="page", status="draft")
    assert rows(html) == []
    assert "nothing matches" in html.lower()


def test_a_value_that_is_not_a_filter_is_ignored_not_an_error(client_as, db_path):
    seed_mix(db_path)
    editor = client_as("editor")
    assert len(rows(listing(editor, type="banana"))) == 6
    assert len(rows(listing(editor, status="banana", type="page"))) == 3
    assert len(rows(listing(editor, type="", status=""))) == 6


def test_the_filter_controls_show_which_filter_is_on_and_keep_the_other(client_as, db_path):
    seed_mix(db_path)
    editor = client_as("editor")
    html = listing(editor, type="post", status="draft")
    on = re.findall(r'<a [^>]*aria-current="true"[^>]*>([^<]+)</a>', html)
    assert sorted(label.strip() for label in on) == ["Draft", "Posts"]
    # Choosing Published from here keeps the Posts filter.
    published = re.search(r'<a [^>]*href="([^"]*)"[^>]*>\s*Published\s*</a>', html)
    assert published
    assert set(titles(editor.get(published.group(1).replace("&amp;", "&")).text)) == {
        "Afrobeat Night", "Movie Evening"}


def test_a_row_shows_title_status_display_name_and_last_updated(client_as, db_path):
    add_account(db_path, "kofi-private", "Kofi A.")
    amara = add_account(db_path, "amara-private", "Amara O.")
    post_id = posts.create(db_path, title="Afrobeat Night", body="x", author_id=amara)
    posts.publish(db_path, post_id)
    page_id = pages.create(db_path, title="About ASA", slug="about-asa", body="x",
                           author_id=amara)
    html = listing(client_as("editor"))
    by_title = {row["title"]: row for row in rows(html)}
    assert by_title["Afrobeat Night"]["status"] == "Published"
    assert by_title["Afrobeat Night"]["author"] == "Amara O."
    assert by_title["About ASA"]["status"] == "Draft"
    assert by_title["About ASA"]["author"] == "Amara O."
    with sqlite3.connect(db_path) as conn:
        post_updated = conn.execute("SELECT updated_at FROM posts WHERE id = ?",
                                    (post_id,)).fetchone()[0]
        page_updated = conn.execute("SELECT updated_at FROM pages WHERE id = ?",
                                    (page_id,)).fetchone()[0]
    assert by_title["Afrobeat Night"]["updated"] == post_updated
    assert by_title["About ASA"]["updated"] == page_updated


def test_a_row_never_shows_the_private_username(client_as, db_path):
    amara = add_account(db_path, "amara-private", "Amara O.")
    posts.create(db_path, title="Afrobeat Night", body="x", author_id=amara)
    for role in ("admin", "editor"):
        assert "amara-private" not in listing(client_as(role))


def test_the_row_follows_a_display_name_change(client_as, db_path):
    amara = add_account(db_path, "amara", "Amara O.")
    posts.create(db_path, title="Afrobeat Night", body="x", author_id=amara)
    editor = client_as("editor")
    assert rows(listing(editor))[0]["author"] == "Amara O."
    accounts.change_display_name(db_path, amara, "ASA Events Team")
    assert rows(listing(editor))[0]["author"] == "ASA Events Team"


def test_a_page_with_no_author_still_lists(client_as, db_path):
    pages.create(db_path, title="Resources", slug="resources", body="x")
    (row,) = rows(listing(client_as("editor")))
    assert row["title"] == "Resources" and row["type"] == "Page"
    assert row["author"] == "—"


def test_a_title_is_escaped_in_the_list(client_as, db_path):
    posts.create(db_path, title="<script>alert(1)</script>", body="x",
                 author_id=author_id(db_path))
    html = listing(client_as("admin"))
    assert "<script>alert(1)</script>" not in html


def test_each_row_links_to_its_editor(client_as, db_path):
    post_id = add_post(db_path, "Afrobeat Night")
    page_id = add_page(db_path, "About ASA")
    editor = client_as("editor")
    hrefs = {row["title"]: row["href"] for row in rows(listing(editor))}
    assert hrefs == {"Afrobeat Night": f"/admin/posts/{post_id}/edit",
                     "About ASA": f"/admin/pages/{page_id}/edit"}
    for href in hrefs.values():
        assert editor.get(href).status_code == 200


def test_the_most_recently_updated_comes_first(client_as, db_path):
    first = add_post(db_path, "First written")
    add_page(db_path, "Middle page")
    add_post(db_path, "Last written")
    assert titles(listing(client_as("editor"))) == [
        "Last written", "Middle page", "First written"]
    posts.update(db_path, first, title="First written", body="corrected")
    assert titles(listing(client_as("editor")))[0] == "First written"


def test_the_dashboard_and_list_link_to_each_other(client_as):
    editor = client_as("editor")
    assert CONTENT in re.findall(r'href="([^"]*)"', editor.get("/admin").text)
    assert "/admin" in re.findall(r'href="([^"]*)"', editor.get(CONTENT).text)


# == both screens follow content changes immediately ===========================

def snapshot(client):
    return counts(client.get("/admin").text), {
        (row["type"], row["title"], row["status"]) for row in rows(listing(client))}


def test_counts_and_list_follow_a_post_through_its_life(client_as):
    from tests.test_t02_posts import create_post, post_to
    admin = client_as("admin")
    zero = dict.fromkeys(FOUR, 0)

    post_id = create_post(admin, "Afrobeat Night")
    assert snapshot(admin) == ({**zero, "draft-posts": 1},
                               {("Post", "Afrobeat Night", "Draft")})

    post_to(admin, f"/admin/posts/{post_id}/publish")
    assert snapshot(admin) == ({**zero, "published-posts": 1},
                               {("Post", "Afrobeat Night", "Published")})

    post_to(admin, f"/admin/posts/{post_id}/unpublish")
    assert snapshot(admin) == ({**zero, "draft-posts": 1},
                               {("Post", "Afrobeat Night", "Draft")})

    post_to(admin, f"/admin/posts/{post_id}/delete")
    assert snapshot(admin) == (zero, set())


def test_counts_and_list_follow_a_page_through_its_life(client_as):
    admin = client_as("admin")
    zero = dict.fromkeys(FOUR, 0)

    page_id = create_page(admin, "About ASA", "about-asa")
    assert snapshot(admin) == ({**zero, "draft-pages": 1},
                               {("Page", "About ASA", "Draft")})

    post_to_page(admin, f"/admin/pages/{page_id}/publish")
    assert snapshot(admin) == ({**zero, "published-pages": 1},
                               {("Page", "About ASA", "Published")})

    post_to_page(admin, f"/admin/pages/{page_id}/unpublish")
    assert snapshot(admin) == ({**zero, "draft-pages": 1},
                               {("Page", "About ASA", "Draft")})

    post_to_page(admin, f"/admin/pages/{page_id}/delete")
    assert snapshot(admin) == (zero, set())


def test_an_editors_edit_shows_in_the_list_straight_away(client_as, db_path):
    from tests.test_t02_posts import create_post, post_to
    editor = client_as("editor")
    post_id = create_post(editor, "Afrobeat Night")
    post_to(editor, f"/admin/posts/{post_id}", title="Afrobeat Night (moved)", body="x")
    assert titles(listing(editor)) == ["Afrobeat Night (moved)"]


def test_the_admin_and_the_editor_see_the_same_content_counts(client_as, db_path):
    seed_mix(db_path)
    assert (counts(client_as("admin").get("/admin").text)
            == counts(client_as("editor").get("/admin").text))


# == usable on a phone =========================================================

@pytest.mark.parametrize("url", ["/admin", CONTENT])
def test_the_screens_are_built_for_a_phone_width(client_as, url):
    html = client_as("editor").get(url).text
    assert re.search(r'<meta name="viewport" content="width=device-width', html)
    assert "<table" not in html           # rows are stacked cards, not a wide table
    assert "@media" in html or "min-width" in html or "flex-wrap" in html


def test_csrf_token_is_still_on_the_dashboard_for_sign_out(client_as):
    assert csrf_token(client_as("editor"), "/admin")
