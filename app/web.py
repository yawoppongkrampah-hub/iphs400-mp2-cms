"""Template rendering for the admin console."""
from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import security, settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES))


def render(request: Request, name: str, status_code: int = 200, **context):
    """Render an admin template with the CSRF token every form needs."""
    context.setdefault("title", "Admin")
    context["csrf_token"] = security.csrf_token(request)
    context["home_path"] = "/admin"
    return templates.TemplateResponse(request, name, context, status_code=status_code)
