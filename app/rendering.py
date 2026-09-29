"""Markdown Body -> safe HTML. The one path for the public export and, later, Preview.

Raw HTML is let through the Markdown parser and then removed by the sanitizer,
so `<script>`, `<iframe>`, `<form>` and event handlers never survive. Only
headings, emphasis, lists, links and images (with alt text) are kept.
"""
from __future__ import annotations

from markdown_it import MarkdownIt

import nh3

_markdown = MarkdownIt("commonmark", {"html": True})

_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "em", "strong",
    "ul", "ol", "li", "a", "img",
}
_ATTRIBUTES = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
_URL_SCHEMES = {"http", "https", "mailto"}


def _keep_attribute(_tag: str, name: str, value: str) -> str | None:
    """Drop root-absolute links and images: the site is served from a subfolder."""
    if name in ("href", "src") and value.strip().startswith("/"):
        return None
    return value


def render_body(markdown: str) -> str:
    return nh3.clean(
        _markdown.render(markdown),
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        url_schemes=_URL_SCHEMES,
        clean_content_tags={"script", "style", "iframe", "form"},
        attribute_filter=_keep_attribute,
    )
