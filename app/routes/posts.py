"""Post screens: list, write, edit, publish, delete, and the Admin-only slug.

Each route names its action in `Depends(require(...))`; the rule table in
app/permissions.py decides who may. Permission is checked before the Post is
looked up.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import posts
from app.permissions import require
from app.web import render

router = APIRouter(prefix="/admin/posts")


def _db(request: Request):
    return request.app.state.database


def _edit_url(request: Request, post_id: int) -> str:
    return request.app.url_path_for("edit_post", post_id=post_id)


def _found(request: Request, post_id: int):
    post = posts.get(_db(request), post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="No such Post.")
    return post


def _form(request: Request, *, post=None, status_code=200, **context):
    return render(request, "admin/post_form.html", status_code=status_code,
                  title="Edit Post" if post else "New Post", user=request.state.user,
                  post=post, **context)


@router.get("", dependencies=[Depends(require("post.list"))])
def post_list(request: Request):
    return render(request, "admin/post_list.html", title="Posts",
                  user=request.state.user, posts=posts.list_all(_db(request)))


@router.get("/new", dependencies=[Depends(require("post.create"))])
def new_post(request: Request):
    return _form(request, title_value="", body_value="")


@router.post("", dependencies=[Depends(require("post.create"))])
def create_post(request: Request, title: str = Form(""), body: str = Form("")):
    try:
        post_id = posts.create(_db(request), title=title, body=body,
                               author_id=request.state.user["id"])
    except posts.PostError as error:
        return _form(request, status_code=400, error=str(error),
                     title_value=title, body_value=body)
    return RedirectResponse(_edit_url(request, post_id), status_code=303)


@router.get("/{post_id}/edit", dependencies=[Depends(require("post.edit"))])
def edit_post(request: Request, post_id: int):
    post = _found(request, post_id)
    return _form(request, post=post, title_value=post["title"], body_value=post["body"])


@router.post("/{post_id}", dependencies=[Depends(require("post.edit"))])
def save_post(request: Request, post_id: int, title: str = Form(""), body: str = Form("")):
    post = _found(request, post_id)
    try:
        posts.update(_db(request), post_id, title=title, body=body)
    except posts.PostError as error:
        return _form(request, post=post, status_code=400, error=str(error),
                     title_value=title, body_value=body)
    return RedirectResponse(_edit_url(request, post_id), status_code=303)


@router.post("/{post_id}/publish", dependencies=[Depends(require("post.publish"))])
def publish_post(request: Request, post_id: int):
    _found(request, post_id)
    posts.publish(_db(request), post_id)
    return RedirectResponse(_edit_url(request, post_id), status_code=303)


@router.post("/{post_id}/unpublish", dependencies=[Depends(require("post.unpublish"))])
def unpublish_post(request: Request, post_id: int):
    _found(request, post_id)
    posts.unpublish(_db(request), post_id)
    return RedirectResponse(_edit_url(request, post_id), status_code=303)


@router.post("/{post_id}/delete", dependencies=[Depends(require("post.delete"))])
def delete_post(request: Request, post_id: int):
    _found(request, post_id)
    posts.delete(_db(request), post_id)
    return RedirectResponse(request.app.url_path_for("post_list"), status_code=303)


@router.get("/{post_id}/slug", dependencies=[Depends(require("post.change_slug"))])
def slug_form(request: Request, post_id: int):
    # The slug form lives on the edit page, beside its warning.
    _found(request, post_id)
    return RedirectResponse(_edit_url(request, post_id) + "#slug", status_code=303)


@router.post("/{post_id}/slug", dependencies=[Depends(require("post.change_slug"))])
def change_slug(request: Request, post_id: int, slug: str = Form("")):
    post = _found(request, post_id)
    try:
        posts.change_slug(_db(request), post_id, slug)
    except posts.PostError as error:
        code = 409 if isinstance(error, posts.SlugTaken) else 400
        return _form(request, post=post, status_code=code, slug_error=str(error),
                     title_value=post["title"], body_value=post["body"])
    return RedirectResponse(_edit_url(request, post_id), status_code=303)
