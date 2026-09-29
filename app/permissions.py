"""The one place that says who may do what.

Every state-changing or Admin-only route asks `require(action)`. Templates ask
`can(role, action)` only to hide controls; hiding is never the protection.
"""
from __future__ import annotations

from fastapi import Request

ADMIN = "admin"
EDITOR = "editor"
EVERYONE = frozenset({ADMIN, EDITOR})
ADMIN_ONLY = frozenset({ADMIN})

RULES: dict[str, frozenset[str]] = {
    "post.list": EVERYONE,
    "post.create": EVERYONE,
    "post.edit": EVERYONE,
    "post.publish": EVERYONE,
    "post.unpublish": EVERYONE,
    "post.delete": ADMIN_ONLY,
    "post.change_slug": ADMIN_ONLY,
}


class PermissionRefused(Exception):
    """The signed-in account's role may not do this action."""


def allowed(role: str, action: str) -> bool:
    # An action missing from the table is refused, never allowed by accident.
    return role in RULES.get(action, frozenset())


def require(action: str):
    """A route dependency: refuse the request unless the role may `action`.

    Runs before the route looks anything up, so an Editor gets the same
    refusal whether or not the thing they asked about exists.
    """
    if action not in RULES:
        raise KeyError(f"unknown action: {action}")

    def check(request: Request) -> None:
        if not allowed(request.state.user["role"], action):
            raise PermissionRefused(action)

    return check
