"""The admin console. Everything under /admin is guarded by security.AdminGuard."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.web import render

router = APIRouter(prefix="/admin")


@router.get("")
def dashboard(request: Request):
    return render(request, "admin/dashboard.html", title="Dashboard",
                  user=request.state.user)
