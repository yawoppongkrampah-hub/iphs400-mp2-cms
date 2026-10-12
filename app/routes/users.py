"""User management: Admin only.

Every route names its action in `Depends(require(...))`, so an Editor is refused
before anything is looked up. No route returns, re-renders or logs a password.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import accounts
from app.permissions import require
from app.web import render

router = APIRouter(prefix="/admin/users")


def _db(request: Request):
    return request.app.state.database


def _account_url(request: Request, user_id: int) -> str:
    return request.app.url_path_for("account_page", user_id=user_id)


def _status_for(error: accounts.AccountError) -> int:
    if isinstance(error, (accounts.UsernameTaken, accounts.WouldLockOutAdmins)):
        return 409
    return 400


def _new_form(request: Request, *, status_code=200, **context):
    context = {"username_value": "", "display_name_value": "", "role_value": "editor",
               **context}
    return render(request, "admin/user_new.html", status_code=status_code,
                  title="New account", user=request.state.user, roles=accounts.ROLES,
                  **context)


def _account(request: Request, user_id: int, *, status_code=200, **context):
    account = accounts.get_user(_db(request), user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="No such account.")
    return render(request, "admin/user_detail.html", status_code=status_code,
                  title="Account", user=request.state.user, account=account,
                  roles=accounts.ROLES, **context)


def _apply(request: Request, user_id: int, change, *, error_key: str):
    """Run an account change; on success go back to the account, else show why."""
    try:
        change()
    except accounts.NoSuchAccount:
        raise HTTPException(status_code=404, detail="No such account.") from None
    except accounts.AccountError as error:
        return _account(request, user_id, status_code=_status_for(error),
                        **{error_key: str(error)})
    return RedirectResponse(_account_url(request, user_id), status_code=303)


@router.get("", dependencies=[Depends(require("user.list"))])
def user_list(request: Request):
    return render(request, "admin/user_list.html", title="Accounts",
                  user=request.state.user, accounts=accounts.list_accounts(_db(request)))


@router.get("/new", dependencies=[Depends(require("user.create"))])
def new_user(request: Request):
    return _new_form(request)


@router.post("", dependencies=[Depends(require("user.create"))])
def create_user(request: Request, username: str = Form(""), password: str = Form(""),
                role: str = Form(""), display_name: str = Form("")):
    try:
        user_id = accounts.create_account(
            _db(request), username=username, password=password, role=role,
            display_name=display_name)
    except accounts.AccountError as error:
        # What was typed comes back, except the password, which never does.
        return _new_form(request, status_code=_status_for(error), error=str(error),
                         username_value=username, display_name_value=display_name,
                         role_value=role)
    return RedirectResponse(_account_url(request, user_id), status_code=303)


@router.get("/{user_id}", dependencies=[Depends(require("user.view"))])
def account_page(request: Request, user_id: int):
    return _account(request, user_id)


@router.post("/{user_id}/role", dependencies=[Depends(require("user.change_role"))])
def change_role(request: Request, user_id: int, role: str = Form("")):
    return _apply(request, user_id,
                  lambda: accounts.change_role(_db(request), user_id, role),
                  error_key="role_error")


@router.post("/{user_id}/deactivate", dependencies=[Depends(require("user.deactivate"))])
def deactivate_user(request: Request, user_id: int):
    return _apply(request, user_id,
                  lambda: accounts.deactivate(_db(request), user_id,
                                              acting_user_id=request.state.user["id"]),
                  error_key="status_error")


@router.post("/{user_id}/reactivate", dependencies=[Depends(require("user.reactivate"))])
def reactivate_user(request: Request, user_id: int):
    return _apply(request, user_id,
                  lambda: accounts.reactivate(_db(request), user_id),
                  error_key="status_error")


@router.post("/{user_id}/password", dependencies=[Depends(require("user.reset_password"))])
def reset_password(request: Request, user_id: int, password: str = Form("")):
    return _apply(request, user_id,
                  lambda: accounts.reset_password(_db(request), user_id, password),
                  error_key="password_error")


@router.post("/{user_id}/display-name",
             dependencies=[Depends(require("user.change_display_name"))])
def change_display_name(request: Request, user_id: int, display_name: str = Form("")):
    return _apply(request, user_id,
                  lambda: accounts.change_display_name(_db(request), user_id, display_name),
                  error_key="display_name_error")
