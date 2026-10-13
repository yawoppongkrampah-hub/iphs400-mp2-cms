"""T07: A polished, accessible public site.

Seam 2 (the published site on disk): seed content, call the publish step into a
temporary folder, and read what it wrote. The pieces already covered by the T03
tests (five-item Home page, ordering, Updated dates) are not repeated here.
"""
import importlib.util
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app import posts, settings
from app.publish import EXCERPT_CHARS, IMAGE_SUFFIXES, card_excerpt, render_site
from app.rendering import render_body
from tests.test_t03_publish import (WELCOME, add_post, all_text, html_files, read,
                                    site_files, titles_in_order)

BRIEF_WELCOME = (
    "ASA is a Kenyon student group primarily for African students and students "
    "with African backgrounds, while welcoming anyone interested in African "
    "cultures and community.")

_spec = importlib.util.spec_from_file_location(
    "seed_demo", settings.ROOT / "scripts" / "seed_demo.py")
seed_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_demo)


@pytest.fixture
def images_dir(tmp_path):
    """A release-holder's folder of approved image files."""
    folder = tmp_path / "approved-images"
    folder.mkdir()
    (folder / "dance.png").write_bytes(b"\x89PNG demo")
    (folder / "crowd.jpg").write_bytes(b"jpeg demo")
    (folder / "pattern.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    return folder


def publish_with(db_path, tmp_path, images):
    return render_site(tmp_path / "site", database=db_path, images=images)


def seed_everything(db_path):
    seed_demo.seed_demo_posts(db_path)
    seed_demo.seed_demo_pages(db_path)


def visible_text(html):
    return re.sub(r"<[^>]+>", " ", html)


def main_nav(html):
    return re.search(r'<nav aria-label="Main">(.*?)</nav>', html, re.S).group(1)


class Outline(HTMLParser):
    """The headings, images and landmarks of one HTML file, in document order."""

    def __init__(self, html):
        super().__init__()
        self.headings, self.images, self.tags, self.lang = [], [], [], None
        self._open = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        if re.fullmatch(r"h[1-6]", tag):
            self._open = [int(tag[1]), ""]
        if tag == "img":
            self.images.append(attrs)

    def handle_data(self, data):
        if self._open:
            self._open[1] += data

    def handle_endtag(self, tag):
        if self._open and tag == f"h{self._open[0]}":
            self.headings.append(tuple(self._open))
            self._open = None

    @property
    def levels(self):
        return [level for level, _ in self.headings]


# -- Welcome text -------------------------------------------------------------

def test_home_page_welcome_uses_exactly_the_client_briefs_wording(db_path, tmp_path):
    out = publish_with(db_path, tmp_path, None)
    assert BRIEF_WELCOME in read(out, "index.html")
    assert WELCOME in BRIEF_WELCOME


def test_the_welcome_comes_before_the_announcements(db_path, tmp_path):
    add_post(db_path, "Afrobeat Night")
    home = read(publish_with(db_path, tmp_path, None), "index.html")
    assert home.index(BRIEF_WELCOME) < home.index("Afrobeat Night")


CLAIMS = ("founded", "established", "since 19", "since 20", "president", "officer",
          "our leaders", "our members", "meets every", "meets on", "weekly",
          "monthly", "award", "oldest", "largest", "history of")


def test_no_claim_about_asa_beyond_the_brief_appears_in_the_export(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    text = visible_text(all_text(out)).replace(BRIEF_WELCOME, "").lower()
    for claim in CLAIMS:
        assert claim not in text, claim


# -- Event cards -----------------------------------------------------------------

def test_home_cards_show_first_published_byline_and_updated(db_path, tmp_path):
    post_id = add_post(db_path, "Afrobeat Night")
    posts.update(db_path, post_id, title="Afrobeat Night", body="Corrected: 8pm")
    out = publish_with(db_path, tmp_path, None)
    day = posts.get(db_path, post_id)["first_published_at"][:10]
    card = re.search(r'<article class="card">.*?</article>', read(out, "index.html"), re.S).group(0)
    assert f'>Posted</span> <time datetime="{day}"' in card
    assert "ASA Events Team" in card
    assert ">Updated</span> <time" in card
    assert "event date" not in card.lower()


def test_republishing_keeps_the_original_first_published_date_and_position(
        db_path, tmp_path):
    post_id = add_post(db_path, "First")
    add_post(db_path, "Second")
    original = posts.get(db_path, post_id)["first_published_at"]
    posts.unpublish(db_path, post_id)
    posts.publish(db_path, post_id)
    assert posts.get(db_path, post_id)["first_published_at"] == original
    out = publish_with(db_path, tmp_path, None)
    assert titles_in_order(read(out, "announcements.html")) == ["Second", "First"]
    assert f'datetime="{original[:10]}"' in read(out, "announcements.html")
    assert "Updated" not in read(out, "announcements.html")


# -- Images: copied into the export, relative paths -----------------------------

def test_approved_image_files_are_copied_into_the_export(db_path, tmp_path, images_dir):
    out = publish_with(db_path, tmp_path, images_dir)
    assert (out / "images/dance.png").read_bytes() == b"\x89PNG demo"
    assert (out / "images/crowd.jpg").exists()
    assert (out / "images/pattern.svg").exists()


def test_only_image_files_are_copied(db_path, tmp_path, images_dir):
    for name in (".env", "notes.txt", "script.py", "page.html", ".DS_Store", "run.js"):
        (images_dir / name).write_text("not an image")
    out = publish_with(db_path, tmp_path, images_dir)
    assert sorted(p.name for p in (out / "images").iterdir()) == [
        "crowd.jpg", "dance.png", "pattern.svg"]


def test_a_missing_images_folder_is_fine(db_path, tmp_path):
    out = publish_with(db_path, tmp_path, tmp_path / "does-not-exist")
    assert (out / "index.html").exists()


def test_image_references_resolve_by_relative_path_from_every_folder(
        db_path, tmp_path, images_dir):
    add_post(db_path, "Photo Post", "![People dancing](images/dance.png)")
    page_id = seed_demo.pages.create(db_path, title="Gallery", slug="gallery",
                                     body="![A crowd](images/crowd.jpg)", author_id=1)
    seed_demo.pages.publish(db_path, page_id)
    out = publish_with(db_path, tmp_path, images_dir)
    assert 'src="../images/dance.png"' in read(out, "posts/photo-post.html")
    assert 'src="images/crowd.jpg"' in read(out, "gallery.html")
    for path in html_files(out):
        for src in re.findall(r'<img [^>]*src="([^"]+)"', path.read_text()):
            assert not src.startswith("/")
            assert (path.parent / src).resolve().is_file(), f"{path.name}: {src}"


@pytest.mark.parametrize("written", ["images/dance.png", "./images/dance.png",
                                     "../images/dance.png", "../../images/dance.png"])
def test_image_references_written_with_dots_still_resolve(
        db_path, tmp_path, images_dir, written):
    add_post(db_path, "Dotted", f"![People dancing]({written})")
    out = publish_with(db_path, tmp_path, images_dir)
    assert 'src="../images/dance.png"' in read(out, "posts/dotted.html")


def test_an_editor_cannot_pull_in_files_outside_the_images_folder(
        db_path, tmp_path, images_dir):
    add_post(db_path, "Sneaky", "![x](/etc/passwd) ![y](//evil.example/a.png)")
    out = publish_with(db_path, tmp_path, images_dir)
    page = read(out, "posts/sneaky.html")
    assert "/etc/passwd" not in page and "evil.example" not in page


# -- The Photos page ---------------------------------------------------------------

def test_the_photos_page_labels_demo_images_illustrative_and_promises_real_ones_later(
        db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    page = read(out, "photos.html")
    images = Outline(page).images
    assert images, "the Photos page shows placeholder images"
    text = visible_text(page).lower()
    assert "actual event photos will be added when asa has permission to use them" in text
    assert text.count("illustrative") >= len(images)
    assert "not a photo of a real asa event" in text or "not a photo of an asa event" in text
    for image in images:
        assert "illustration" in image["alt"].lower()


def test_demo_illustrations_are_never_called_real_event_photos(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for path in html_files(out):
        text = visible_text(path.read_text()).lower()
        assert "photo of the" not in text and "photos from our" not in text


def test_the_repos_demo_images_are_all_present_in_the_export(db_path, tmp_path):
    originals = sorted(p.name for p in settings.IMAGES.iterdir()
                       if p.suffix.lower() in IMAGE_SUFFIXES)
    assert originals, "images/ holds the demo illustrations"
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    assert sorted(p.name for p in (out / "images").iterdir()) == originals


# -- Accessibility ------------------------------------------------------------------

BODY_WITH_BAD_HEADINGS = "# Big title\n\n#### Deep one\n\n## Medium\n\n###### Deepest\n"


def test_every_page_has_one_h1_and_headings_never_skip_a_level(db_path, tmp_path):
    seed_everything(db_path)
    add_post(db_path, "Headings Post", BODY_WITH_BAD_HEADINGS)
    add_post(db_path, "Another")
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    assert len(html_files(out)) > 5
    for path in html_files(out):
        levels = Outline(path.read_text()).levels
        assert levels[0] == 1, f"{path.name}: {levels}"
        assert levels.count(1) == 1, f"{path.name}: {levels}"
        for before, after in zip(levels, levels[1:]):
            assert after <= before + 1, f"{path.name}: {levels}"


def test_body_headings_are_kept_below_the_page_title(db_path, tmp_path):
    add_post(db_path, "Headings Post", BODY_WITH_BAD_HEADINGS)
    page = read(publish_with(db_path, tmp_path, None), "posts/headings-post.html")
    assert Outline(page).levels == [1, 2, 3, 2, 3]


def test_render_body_keeps_sibling_headings_at_the_same_level():
    html = render_body("## One\n\n## Two\n\n### Sub\n")
    assert [m for m in re.findall(r"<h(\d)>", html)] == ["2", "2", "3"]


def test_every_image_in_the_export_has_descriptive_alt_text(db_path, tmp_path, images_dir):
    add_post(db_path, "Described", "![Dancers at a past event](images/dance.png)\n\n"
             "![](images/crowd.jpg)\n\n<img src=\"images/crowd.jpg\">")
    out = publish_with(db_path, tmp_path, images_dir)
    seen = 0
    for path in html_files(out):
        for image in Outline(path.read_text()).images:
            seen += 1
            assert image.get("alt", "").strip(), f"{path.name}: {image}"
    assert seen >= 3
    assert 'alt="Dancers at a past event"' in read(out, "posts/described.html")


def test_an_image_whose_title_mentions_alt_still_gets_a_fallback(db_path, tmp_path):
    add_post(db_path, "Tricky", '<img src="images/a.png" title="alt=fake">')
    page = read(publish_with(db_path, tmp_path, None), "posts/tricky.html")
    assert all(image.get("alt", "").strip() for image in Outline(page).images)


def test_every_page_is_a_complete_phone_friendly_document(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for path in html_files(out):
        html = path.read_text()
        outline = Outline(html)
        assert html.lower().startswith("<!doctype html>"), path.name
        assert outline.lang == "en", path.name
        assert 'name="viewport" content="width=device-width, initial-scale=1"' in html
        assert "<title>" in html and "<main" in html and 'aria-label="Main"' in html


def test_there_is_a_skip_link_to_the_main_content(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for path in html_files(out):
        html = path.read_text()
        link = re.search(r'<body[^>]*>\s*<a class="skip-link" href="#([^"]+)"', html)
        assert link, path.name
        assert f'id="{link.group(1)}"' in html.split("<main", 1)[1].split(">", 1)[0] + ">", path.name


def test_the_current_page_is_marked_in_the_navigation(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for name, label in (("announcements.html", "Announcements"), ("photos.html", "Photos"),
                        ("posts/afrobeat-event-demo-placeholder.html", "Announcements")):
        nav = main_nav(read(out, name))
        current = re.findall(r'<a [^>]*aria-current="page"[^>]*>([^<]+)</a>', nav)
        assert current == [label], (name, current)
    assert "aria-current" not in main_nav(read(out, "index.html"))


def _tokens(block):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_text_and_link_colours_are_readable_in_light_and_dark(db_path, tmp_path):
    css = read(publish_with(db_path, tmp_path, None), "style.css")
    dark_start = css.index("prefers-color-scheme: dark")
    light, dark = _tokens(css[:dark_start]), _tokens(css[dark_start:])
    pairs = [("text", "bg"), ("text", "surface"), ("muted", "bg"), ("muted", "surface"),
             ("link", "bg"), ("link", "surface"), ("on-accent", "accent"),
             ("focus", "bg"), ("focus", "surface"), ("text", "soft"), ("link", "soft"),
             ("on-gold", "gold"), ("on-green", "green"), ("hero-text", "hero-bg"),
             ("hero-soft", "hero-bg"), ("gold", "hero-bg"), ("hero-focus", "hero-bg")]
    for name, tokens in (("light", light), ("dark", dark)):
        for fore, back in pairs:
            ratio = contrast(tokens[fore], tokens[back])
            needed = 3.0 if fore in ("focus", "hero-focus") else 4.5
            assert ratio >= needed, f"{name}: {fore} on {back} is {ratio:.2f}:1"


def test_focus_is_visible_and_the_layout_adapts_to_a_phone(db_path, tmp_path):
    css = read(publish_with(db_path, tmp_path, None), "style.css")
    assert ":focus-visible" in css
    assert "outline: none" not in css and "outline:none" not in css
    assert re.search(r"img\s*\{[^}]*max-width:\s*100%", css)
    for width in re.findall(r"(?<!max-)(?<!-)width:\s*(\d+)px", css):
        assert int(width) <= 390, f"fixed width {width}px"


def test_nothing_in_the_styles_loads_from_outside_the_site(db_path, tmp_path):
    css = read(publish_with(db_path, tmp_path, None), "style.css")
    assert "http" not in css and "@import" not in css and "url(/" not in css


# -- Relative paths and Drafts, over the whole seeded export -------------------------

def test_the_whole_seeded_export_is_relative_and_has_no_drafts(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for path in html_files(out):
        for value in re.findall(r'(?:href|src)="([^"]*)"', path.read_text()):
            assert not value.startswith("/"), f"{path.name}: {value}"
    text = all_text(out)
    assert "Draft idea" not in text and "Get involved" not in text
    assert not any("draft" in p.name or "get-involved" in p.name for p in site_files(out))
    assert titles_in_order(read(out, "announcements.html")) == [
        "Afrobeat event (demo placeholder)"]


# -- Warm redesign: header, hero, illustration, cards, Instagram ----------------------

INSTAGRAM = "https://www.instagram.com/asa.kenyon/"
FULL_NAME = settings.SITE_TITLE


def test_the_full_name_is_not_repeated_in_the_header_and_the_hero(db_path, tmp_path):
    seed_everything(db_path)
    home = read(publish_with(db_path, tmp_path, settings.IMAGES), "index.html")
    header = home.split("<header", 1)[1].split("</header>", 1)[0]
    hero = home.split('<section class="hero">', 1)[1].split("</section>", 1)[0]
    assert FULL_NAME not in header and settings.SITE_SHORT_TITLE in header
    assert re.search(r"<h1>\s*%s\s*</h1>" % FULL_NAME, hero)
    assert visible_text(home.split("</header>", 1)[1]).count(FULL_NAME) == 1


def test_every_page_links_to_the_instagram_account_safely(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    link = r'<a [^>]*href="%s"[^>]*>' % re.escape(INSTAGRAM)
    for path in html_files(out):
        html = path.read_text()
        footer = html.split("<footer>", 1)[1]
        assert re.search(link, footer), f"{path.name}: no footer link"
        assert all('rel="noopener"' in found for found in re.findall(link, html)), path.name
        # The hero button is on the Home page only.
        assert len(re.findall(link, html)) == (2 if path.name == "index.html" else 1), path.name


def test_the_hero_illustration_is_decorative_inline_and_not_a_photo_claim(db_path, tmp_path):
    home = read(publish_with(db_path, tmp_path, None), "index.html")
    art = re.search(r"<svg[^>]*>", home).group(0)
    assert 'aria-hidden="true"' in art and 'focusable="false"' in art
    hero = home.split('<section class="hero">', 1)[1].split("</section>", 1)[0]
    assert "<img" not in hero
    assert "photo" not in visible_text(hero).lower()


def test_the_navigation_lists_the_three_starter_pages_when_published(db_path, tmp_path):
    seed_everything(db_path)
    out = publish_with(db_path, tmp_path, settings.IMAGES)
    for name in ("index.html", "announcements.html", "posts/afrobeat-event-demo-placeholder.html"):
        links = re.findall(r'<a [^>]*>([^<]+)</a>', main_nav(read(out, name)))
        assert links == ["Announcements", "About ASA", "Resources", "Photos"], name


def test_event_cards_show_dates_byline_excerpt_and_one_link(db_path, tmp_path):
    add_post(db_path, "Afrobeat Night", "Join us for **music**, food.\n\n- What: a party\n")
    card = read(publish_with(db_path, tmp_path, None), "index.html").split(
        '<article class="card">', 1)[1].split("</article>", 1)[0]
    assert "Posted" in card and "By " in card
    assert "Join us for music, food. What: a party" in card
    assert card.count("<a ") == 1


def test_a_long_card_excerpt_is_cut_at_a_word_with_an_ellipsis():
    text = card_excerpt("<p>" + "word " * 100 + "</p>")
    assert text.endswith("word…") and len(text) <= EXCERPT_CHARS + 1


def test_an_excerpt_keeps_a_word_that_ends_exactly_on_the_limit():
    lead = "a" * (EXCERPT_CHARS - 5)               # lead + " last" is exactly EXCERPT_CHARS long
    assert card_excerpt(f"<p>{lead} last more words</p>") == f"{lead} last…"


def test_an_excerpt_cuts_one_unbroken_word_at_the_limit():
    assert card_excerpt("<p>" + "x" * 400 + "</p>") == "x" * EXCERPT_CHARS + "…"


@pytest.mark.parametrize("body_html, expected", [
    ("", ""),
    ('<p><img alt="A" src="images/a.png"></p>', ""),
    ("<h2>What</h2><p>Party at nine</p>", "What Party at nine"),
    ("<ul><li>What: a party</li><li>When: soon</li></ul>", "What: a party · When: soon"),
    ("<p>Tom &amp; Jerry <strong>night</strong>, 8pm</p>", "Tom & Jerry night, 8pm"),
])
def test_card_excerpt_edge_cases(body_html, expected):
    assert card_excerpt(body_html) == expected


def test_a_card_for_a_post_with_no_text_has_no_excerpt_paragraph(db_path, tmp_path):
    add_post(db_path, "Picture only", "![A drawing of a sun](images/demo-illustration-1.svg)\n")
    home = read(publish_with(db_path, tmp_path, None), "index.html")
    assert 'class="excerpt"' not in home and "Picture only" in home


def test_a_card_excerpt_cannot_carry_markup(db_path, tmp_path):
    add_post(db_path, "Sneaky", "Hello <script>alert(1)</script> **there** <b>x</b>\n")
    home = read(publish_with(db_path, tmp_path, None), "index.html")
    excerpt = re.search(r'<p class="excerpt">(.*?)</p>', home, re.S).group(1)
    assert "<" not in excerpt and "alert" not in excerpt


# -- Review follow-ups: focus and motion ------------------------------------------------

def test_the_link_keeps_its_own_focus_ring_where_has_is_unsupported(db_path, tmp_path):
    css = read(publish_with(db_path, tmp_path, None), "style.css")
    assert css.count("outline-color: transparent") == 1
    rule = next(line for line in css.splitlines() if "outline-color: transparent" in line)
    assert rule.lstrip().startswith("@supports selector(:has(*))")


def test_smooth_scrolling_is_only_for_people_who_have_not_asked_for_less_motion(
        db_path, tmp_path):
    css = read(publish_with(db_path, tmp_path, None), "style.css")
    assert css.count("scroll-behavior") == 1
    assert css.index("scroll-behavior") > css.index("prefers-reduced-motion: no-preference")
