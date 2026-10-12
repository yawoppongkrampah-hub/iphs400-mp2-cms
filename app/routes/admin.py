"""The admin console. Everything under /admin is guarded by security.AdminGuard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app import accounts, content
from app.permissions import allowed, require
from app.web import render

router = APIRouter(prefix="/admin")


@router.get("")
def dashboard(request: Request):
    user, database = request.state.user, request.app.state.database
    # Account numbers are fetched only for the Admin, so they never reach an
    # Editor's page even by mistake in the template.
    account_counts = (accounts.count_by_status(database)
                      if allowed(user["role"], "dashboard.account_counts") else None)
    return render(request, "admin/dashboard.html", title="Dashboard", user=user,
                  counts=content.counts(database), account_counts=account_counts)


@router.get("/content", dependencies=[Depends(require("content.list"))])
def content_list(request: Request, kind: str = Query("", alias="type"), status: str = ""):
    # A value that is not a filter is ignored, so a stale link shows everything.
    kind = kind if kind in content.TYPES else None
    status = status if status in content.STATUSES else None
    items = content.list_items(request.app.state.database, kind=kind, status=status)
    return render(request, "admin/content_list.html", title="Content",
                  user=request.state.user, items=items, kind=kind, status=status)
