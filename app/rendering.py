"""Markdown Body -> safe HTML. The one path for the public export and, later, Preview.

Raw HTML is let through the Markdown parser and then removed by the sanitizer,
so `<script>`, `<iframe>`, `<form>` and event handlers never survive. Only
headings, emphasis, lists, links and images (with alt text) are kept.

Two things keep the page accessible whatever an Editor types: headings in a Body
are moved below the page's own <h1> without skipping a level, and an image with
no alt text gets a plain fallback instead of none.
"""
from __future__ import annotations

import re

from markdown_it import MarkdownIt

import nh3

_markdown = MarkdownIt("commonmark", {"html": True})

_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "em", "strong",
    "ul", "ol", "li", "a", "img",
}
_ATTRIBUTES = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
_URL_SCHEMES = {"http", "https", "mailto"}

# Approved image files are copied to <site>/images/. An Editor always writes
# `images/<file>`; each page adds the `root` that gets from there to the site root.
NO_ALT = "Image without a description"

_HEADING = re.compile(r"<(/?)h([1-6])>")
_IMG_WITHOUT_ALT = re.compile(r"<img(?![^>]*\salt=)")
# `images/x.png`, `./images/x.png` and `../images/x.png` all mean the approved-images folder.
_IMAGES_REFERENCE = re.compile(r"^(?:\.{1,2}/)*(images/.*)$", re.S)


def _attribute_filter(root: str):
    def keep(tag: str, name: str, value: str) -> str | None:
        """Drop root-absolute links and images (the site is served from a
        subfolder), point `images/...` at the site root, and never leave alt empty."""
        if name in ("href", "src") and value.strip().startswith("/"):
            return None
        if tag == "img" and name == "src":
            reference = _IMAGES_REFERENCE.match(value)
            if reference:
                return root + reference.group(1)
        if tag == "img" and name == "alt" and not value.strip():
            return NO_ALT
        return value

    return keep


def _nest_headings(html: str) -> str:
    """Body headings start at <h2> and never skip a level.

    The page's own title is the only <h1>. A heading may be at most one level
    deeper than the one before it; siblings stay siblings.
    """
    last_level = 1      # the page's own <h1>
    open_level = 2      # level of the heading currently open

    def fix(match: re.Match) -> str:
        nonlocal last_level, open_level
        if match.group(1):
            return f"</h{open_level}>"
        open_level = min(max(int(match.group(2)), 2), last_level + 1)
        last_level = open_level
        return f"<h{open_level}>"

    return _HEADING.sub(fix, html)


def render_body(markdown: str, root: str = "") -> str:
    """`root` is the relative path from the page to the site root ("" or "../")."""
    html = nh3.clean(
        _markdown.render(markdown),
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        url_schemes=_URL_SCHEMES,
        clean_content_tags={"script", "style", "iframe", "form"},
        attribute_filter=_attribute_filter(root),
    )
    html = _IMG_WITHOUT_ALT.sub(f'<img alt="{NO_ALT}"', html)
    return _nest_headings(html)
