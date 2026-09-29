"""Who is signed in, and CSRF protection.

The session is a signed cookie (Starlette SessionMiddleware). It holds only the
account id and a CSRF token. The account is looked up on every request, so a
Deactivated account stops working immediately.
"""
from __future__ import annotations

import secrets
import sqlite3

from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app import accounts

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def current_user(request: Request) -> sqlite3.Row | None:
    """The signed-in, active account for this request, or None."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = accounts.get_user(request.app.state.database, user_id)
    if user is None or not user["active"]:
        request.session.clear()
        return None
    return user


def sign_in(request: Request, user: sqlite3.Row) -> None:
    # A fresh session (and CSRF token) on sign-in, so nothing from before it lives on.
    request.session.clear()
    request.session["user_id"] = user["id"]


def sign_out(request: Request) -> None:
    request.session.clear()


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = request.session["csrf"] = secrets.token_urlsafe(32)
    return token


async def verify_csrf(request: Request) -> None:
    """Reject any state-changing request that lacks this session's token.

    Registered on the whole app, so a new route cannot forget it.
    """
    if request.method in SAFE_METHODS:
        return
    expected = request.session.get("csrf")
    form = await request.form()
    supplied = form.get("csrf_token") or ""
    if not expected or not secrets.compare_digest(str(supplied), expected):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


class AdminGuard:
    """Send anyone who is not signed in away from every /admin address.

    A middleware rather than a per-route check, so it also covers addresses
    that do not exist (they must not answer differently to a signed-out visitor).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and (
                scope["path"] == "/admin" or scope["path"].startswith("/admin/")):
            request = Request(scope, receive)
            user = current_user(request)
            if user is None:
                await RedirectResponse("/login", status_code=303)(scope, receive, send)
                return
            scope.setdefault("state", {})["user"] = user
        await self.app(scope, receive, send)
