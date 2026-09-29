"""Sign in and sign out."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import accounts, security
from app.web import render

router = APIRouter()

# One message for every failure, so it never reveals which part was wrong.
GENERIC_FAILURE = "Incorrect username or password."


@router.get("/login")
def login_form(request: Request):
    if security.current_user(request):
        return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)
    return render(request, "admin/login.html", title="Sign in")


@router.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    user = accounts.authenticate(request.app.state.database, username, password)
    if user is None:
        return render(request, "admin/login.html", status_code=401,
                      title="Sign in", error=GENERIC_FAILURE)
    security.sign_in(request, user)
    return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)


@router.post("/logout")
def logout(request: Request):
    security.sign_out(request)
    return RedirectResponse(request.app.url_path_for("login_form"), status_code=303)
