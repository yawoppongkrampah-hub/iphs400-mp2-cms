"""The FastAPI application.

The admin console lives under /admin (signed-in only), with /login and /logout
beside it; the public site preview answers at /.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from app import security, settings
from app.permissions import PermissionRefused
from app.publish import WELCOME
from app.routes import admin, auth, posts
from app.web import render, templates

SESSION_LIFETIME_SECONDS = 8 * 60 * 60


def create_app(database: Path | None = None) -> FastAPI:
    # Every state-changing request is CSRF-checked, whatever route it reaches.
    app = FastAPI(title="IPHS 400 MP2 CMS",
                  dependencies=[Depends(security.verify_csrf)])
    app.state.database = database or settings.DATABASE_PATH

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(posts.router)

    @app.exception_handler(PermissionRefused)
    def refuse(request: Request, _: PermissionRefused):
        return render(request, "admin/refused.html", status_code=403,
                      title="No permission", user=request.state.user)

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "site_title": settings.SITE_TITLE,
             "root": "", "welcome": WELCOME, "posts": []},
        )

    # Middleware added last is outermost: the session must be loaded before the
    # guard runs, and saved after it.
    app.add_middleware(security.AdminGuard)
    app.add_middleware(
        SessionMiddleware, secret_key=settings.SECRET_KEY, session_cookie="cms_session",
        max_age=SESSION_LIFETIME_SECONDS, same_site="lax",
    )
    return app


app = create_app()
