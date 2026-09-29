"""Admin navigation and form actions come from named routes and really work.

Seam 1 (the admin console over HTTP): every link an admin screen shows leads
somewhere that answers, and every form posts to the route it means, including
the nested /admin/posts/{id}/... routes.
"""
import re
from pathlib import Path

from app import settings
from tests.conftest import DEMO_USERS, csrf_token
from tests.test_t02_posts import create_post, edit_page, is_refusal, post_to

LINK = re.compile(r'<a [^>]*href="([^"]*)"')
FORM = re.compile(r'<form [^>]*action="([^"]*)"')


def local_links(html):
    return [h for h in LINK.findall(html) if h.startswith("/")]


def form_actions(html):
    return FORM.findall(html)


def test_admin_templates_hard_code_no_root_absolute_path():
    for path in (settings.TEMPLATES / "admin").glob("*.html"):
        text = path.read_text()
        for attr in ('href="/', 'src="/', 'action="/'):
            assert attr not in text, f"{path.name} writes {attr}...\" by hand"


def test_every_link_reachable_from_the_dashboard_answers(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    seen, queue = set(), ["/admin"]
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        seen.add(url)
        response = admin.get(url)
        assert response.status_code == 200, f"{url} -> {response.status_code}"
        queue += [u for u in local_links(response.text) if u not in seen]
    # the crawl really walked the nested routes, not just the top level
    assert {"/admin", "/admin/posts", "/admin/posts/new",
            f"/admin/posts/{post_id}/edit"} <= seen


def test_post_form_actions_point_at_the_nested_routes(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    base = f"/admin/posts/{post_id}"
    assert form_actions(edit_page(admin, post_id)) == [
        base, f"{base}/publish", f"{base}/slug", f"{base}/delete"]
    admin_new = admin.get("/admin/posts/new").text
    assert form_actions(admin_new) == ["/admin/posts"]


def test_each_form_action_on_the_edit_page_does_its_job(client_as):
    admin = client_as("admin")
    post_id = create_post(admin, "Afrobeat Night")
    edit_url = f"/admin/posts/{post_id}/edit"

    def submit_form(index, **data):
        action = form_actions(edit_page(admin, post_id))[index]
        return post_to(admin, action, **data)

    saved = submit_form(0, title="Afrobeat Night 2", body="new body")
    assert saved.status_code == 303 and saved.headers["location"] == edit_url
    assert "Afrobeat Night 2" in edit_page(admin, post_id)

    published = submit_form(1)
    assert published.headers["location"] == edit_url
    assert 'id="post-status">Published<' in edit_page(admin, post_id)

    # once Published, the second form becomes Unpublish and still works
    unpublished = submit_form(1)
    assert unpublished.headers["location"] == edit_url
    assert 'id="post-status">Draft<' in edit_page(admin, post_id)

    slugged = submit_form(2, slug="afrobeat-night-final")
    assert slugged.headers["location"] == edit_url
    assert "afrobeat-night-final" in edit_page(admin, post_id)

    deleted = submit_form(3)
    assert deleted.status_code == 303 and deleted.headers["location"] == "/admin/posts"
    assert admin.get(edit_url).status_code == 404


def test_signed_out_sign_in_form_posts_and_sign_out_form_returns_to_it(client):
    (action,) = form_actions(client.get("/login").text)
    assert action == "/login"
    user = DEMO_USERS["admin"]
    signed_in = client.post(action, data={
        "username": user["username"], "password": user["password"],
        "csrf_token": csrf_token(client)}, follow_redirects=False)
    assert signed_in.status_code == 303 and signed_in.headers["location"] == "/admin"

    dashboard = client.get("/admin").text
    assert "/admin/posts" in local_links(dashboard)
    (logout,) = form_actions(dashboard)
    signed_out = post_to(client, logout)
    assert signed_out.status_code == 303 and signed_out.headers["location"] == "/login"
    assert client.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_the_permission_refusal_page_links_back_to_the_dashboard(client_as):
    admin, editor = client_as("admin"), client_as("editor")
    post_id = create_post(editor, "Afrobeat Night")
    refused = post_to(editor, f"/admin/posts/{post_id}/delete")
    assert is_refusal(refused)
    links = local_links(refused.text)
    assert links and set(links) == {"/admin"}
    assert "Back to the dashboard" in refused.text
    assert editor.get("/admin").status_code == 200
    assert admin.get("/admin").status_code == 200
