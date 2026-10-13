"""Preview: the rendered, sanitized Body as the public page will show it.

Preview calls the same `render_body` as the export, with the same roots, so what
an Editor sees is what goes Live. It reads the text in the form and saves nothing,
and it reads no other field, so it cannot be used to change a Post or a Page. Any
signed-in role may use it, and the page it returns has none of the Admin-only
controls.

The images a Body points at (`images/<file>`) are shown by the console itself,
from the same approved-images folder `cms publish` copies.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse

from app import pages, settings
from app.permissions import require
from app.publish import is_approved_image
from app.rendering import PAGE_ROOT, POST_ROOT, render_body
from app.web import render

router = APIRouter(prefix="/admin")


def _image_base(request: Request) -> str:
    """The folder that holds `images/`, so a Body's relative image links resolve under /admin."""
    return request.app.url_path_for("preview_image", path="").removesuffix("images/")


def _preview(request: Request, *, kind: str, title: str, body: str, root: str,
             base: str):
    return render(request, "admin/preview.html", title=f"Preview of the {kind}",
                  user=request.state.user, kind=kind, page_title=title.strip() or "(untitled)",
                  body_html=render_body(body, root=root), base_href=base)


@router.post("/posts/preview", dependencies=[Depends(require("preview.view"))])
def preview_post(request: Request, title: str = Form(""), body: str = Form("")):
    # A Post's page sits one folder down (posts/<slug>.html), as in the export.
    return _preview(request, kind="Post", title=title, body=body, root=POST_ROOT,
                    base=_image_base(request) + "posts/")


@router.post("/pages/{page_id}/preview", dependencies=[Depends(require("preview.view"))])
def preview_page(request: Request, page_id: int, body: str = Form("")):
    # The title is the Page's saved title: an Editor cannot retitle a Page, so it is not a field.
    page = pages.get(request.app.state.database, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="No such Page.")
    return _preview(request, kind="Page", title=page["title"], body=body, root=PAGE_ROOT,
                    base=_image_base(request))


@router.get("/preview/images/{path:path}", dependencies=[Depends(require("preview.view"))])
def preview_image(path: str):
    target = settings.IMAGES / path
    if not is_approved_image(settings.IMAGES, target):
        raise HTTPException(status_code=404, detail="No such image.")
    # A direct visit to an SVG must not run anything: sandbox it.
    return FileResponse(target, headers={"Content-Security-Policy": "sandbox"})
