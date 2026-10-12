"""Page screens: list, create, edit the Body, and the Admin-only structure controls.

Every Page action has its own route and its own rule in app/permissions.py, so
an Editor's direct submission to an Admin-only route is refused by the server
whatever the form on their screen shows. Permission is checked before the Page
is looked up. The Body route reads only `body`: anything else in the submission
is ignored.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import pages
from app.permissions import require
from app.web import render

router = APIRouter(prefix="/admin/pages")


def _db(request: Request):
    return request.app.state.database


def _edit_url(request: Request, page_id: int) -> str:
    return request.app.url_path_for("edit_page", page_id=page_id)


def _found(request: Request, page_id: int):
    page = pages.get(_db(request), page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="No such Page.")
    return page


def _new_form(request: Request, *, status_code=200, **context):
    return render(request, "admin/page_new.html", status_code=status_code,
                  title="New Page", user=request.state.user, **context)


def _edit_form(request: Request, page, *, status_code=200, **context):
    return render(request, "admin/page_form.html", status_code=status_code,
                  title="Edit Page", user=request.state.user, page=page, **context)


@router.get("", dependencies=[Depends(require("page.list"))])
def page_list(request: Request):
    return render(request, "admin/page_list.html", title="Pages",
                  user=request.state.user, pages=pages.list_all(_db(request)))


@router.get("/new", dependencies=[Depends(require("page.create"))])
def new_page(request: Request):
    return _new_form(request, title_value="", slug_value="", body_value="")


@router.post("", dependencies=[Depends(require("page.create"))])
def create_page(request: Request, title: str = Form(""), slug: str = Form(""),
                body: str = Form("")):
    try:
        page_id = pages.create(_db(request), title=title, slug=slug, body=body,
                               author_id=request.state.user["id"])
    except pages.PageError as error:
        code = 409 if isinstance(error, pages.PageSlugTaken) else 400
        return _new_form(request, status_code=code, error=str(error),
                         title_value=title, slug_value=slug, body_value=body)
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.get("/{page_id}/edit", dependencies=[Depends(require("page.edit_body"))])
def edit_page(request: Request, page_id: int):
    return _edit_form(request, _found(request, page_id))


@router.post("/{page_id}", dependencies=[Depends(require("page.edit_body"))])
def save_page_body(request: Request, page_id: int, body: str = Form("")):
    _found(request, page_id)
    pages.update_body(_db(request), page_id, body)
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.post("/{page_id}/title", dependencies=[Depends(require("page.retitle"))])
def retitle_page(request: Request, page_id: int, title: str = Form("")):
    page = _found(request, page_id)
    try:
        pages.retitle(_db(request), page_id, title)
    except pages.PageError as error:
        return _edit_form(request, page, status_code=400, title_error=str(error))
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.post("/{page_id}/slug", dependencies=[Depends(require("page.change_slug"))])
def change_page_slug(request: Request, page_id: int, slug: str = Form("")):
    page = _found(request, page_id)
    try:
        pages.change_slug(_db(request), page_id, slug)
    except pages.PageError as error:
        code = 409 if isinstance(error, pages.PageSlugTaken) else 400
        return _edit_form(request, page, status_code=code, slug_error=str(error))
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.post("/{page_id}/publish", dependencies=[Depends(require("page.publish"))])
def publish_page(request: Request, page_id: int):
    _found(request, page_id)
    pages.publish(_db(request), page_id)
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.post("/{page_id}/unpublish", dependencies=[Depends(require("page.unpublish"))])
def unpublish_page(request: Request, page_id: int):
    _found(request, page_id)
    pages.unpublish(_db(request), page_id)
    return RedirectResponse(_edit_url(request, page_id), status_code=303)


@router.post("/{page_id}/delete", dependencies=[Depends(require("page.delete"))])
def delete_page(request: Request, page_id: int):
    _found(request, page_id)
    pages.delete(_db(request), page_id)
    return RedirectResponse(request.app.url_path_for("page_list"), status_code=303)
