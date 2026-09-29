"""Template rendering for the admin console."""
from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app import permissions, security, settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
# Templates use this only to hide controls; the server still checks every request.
templates.env.globals["can"] = permissions.allowed


@pass_context
def route(context, name: str, **params) -> str:
    """The path of a named route, e.g. route('edit_post', post_id=3).

    Templates use this instead of writing "/admin/..." by hand, so a link or
    form action follows its route if the route's path ever changes.
    """
    return context["request"].app.url_path_for(name, **params)


templates.env.globals["route"] = route


def render(request: Request, name: str, status_code: int = 200, **context):
    """Render an admin template with the CSRF token every form needs."""
    context.setdefault("title", "Admin")
    context["csrf_token"] = security.csrf_token(request)
    context["home_path"] = request.app.url_path_for("dashboard")
    return templates.TemplateResponse(request, name, context, status_code=status_code)
