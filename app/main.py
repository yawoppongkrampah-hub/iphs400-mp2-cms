"""The FastAPI application.

The admin console lives under /admin (signed-in only), with /login and /logout
beside it; the public site preview answers at /.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app import security, settings
from app.permissions import PermissionRefused
from app.publish import WELCOME
from app.routes import admin, auth, pages, posts, preview, users
from app.web import render, templates

SESSION_LIFETIME_SECONDS = 8 * 60 * 60


def create_app(database: Path | None = None) -> FastAPI:
    # Every state-changing request is CSRF-checked, whatever route it reaches.
    app = FastAPI(title="IPHS 400 MP2 CMS",
                  dependencies=[Depends(security.verify_csrf)])
    app.state.database = database or settings.DATABASE_PATH

    app.include_router(auth.router)
    app.include_router(admin.router)
    # Before posts and pages: /admin/posts/preview must not be read as a Post id.
    app.include_router(preview.router)
    app.include_router(posts.router)
    app.include_router(pages.router)
    app.include_router(users.router)

    @app.exception_handler(PermissionRefused)
    def refuse(request: Request, _: PermissionRefused):
        return render(request, "admin/refused.html", status_code=403,
                      title="No permission", user=request.state.user)

    def error_page(request: Request, status_code: int, heading: str, message: str):
        """A readable page, with the navigation when signed in, instead of raw JSON."""
        user = getattr(request.state, "user", None)
        back_route, back_label = (("dashboard", "Back to the dashboard") if user
                                  else ("login_form", "Go to sign in"))
        return render(request, "admin/error.html", status_code=status_code, title=heading,
                      user=user, heading=heading, message=message,
                      back_url=request.app.url_path_for(back_route), back_label=back_label)

    @app.exception_handler(StarletteHTTPException)
    def http_error(request: Request, error: StarletteHTTPException):
        if error.status_code == 403 and error.detail == security.CSRF_FAILURE:
            return error_page(request, 403, "That form could not be sent",
                              "The security token on the form was missing or out of date, "
                              "so nothing was changed. Go back, reload the page and try again.")
        if error.status_code == 404:
            detail = str(error.detail)
            message = detail if detail.startswith("No such") else "That address does not exist."
            return error_page(request, 404, "Not found", message)
        return error_page(request, error.status_code, "Something went wrong", str(error.detail))

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, _: RequestValidationError):
        return error_page(request, 422, "That request was not understood",
                          "Something in the address or form was not valid. Nothing was changed.")

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
