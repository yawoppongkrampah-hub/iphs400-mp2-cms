"""Accounts: creating them, hashing passwords, checking sign-in.

A password is never stored, returned or logged in plain form; only the argon2
hash is kept. The username is private (sign-in only); the Display name is the
public byline. Accounts are deactivated, never deleted.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.db import connect

ROLES = ("admin", "editor")
MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher()
# Checked when the username is unknown, so a miss takes as long as a wrong
# password and timing does not reveal which usernames exist.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


class AccountError(ValueError):
    """A request to create an account that cannot be honoured."""


class UsernameTaken(AccountError):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _password_matches(stored_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_account(path: Path, *, username: str, password: str, role: str,
                   display_name: str) -> int:
    username, display_name = username.strip(), display_name.strip()
    if not username or not display_name:
        raise AccountError("A username and a Display name are required.")
    if role not in ROLES:
        raise AccountError(f"Role must be one of: {', '.join(ROLES)}.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(
            f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")
    try:
        with closing(connect(path)) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role, display_name) "
                "VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, display_name),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise UsernameTaken(f"An account named '{username}' already exists.") from None


def authenticate(path: Path, username: str, password: str) -> sqlite3.Row | None:
    """Return the account for a correct username and password, else None.

    An unknown username, a wrong password and a Deactivated account all return
    None, so the caller can give one generic message for all three.
    """
    with closing(connect(path)) as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    matches = _password_matches(user["password_hash"] if user else _DUMMY_HASH,
                                password)
    if user is None or not matches or not user["active"]:
        return None
    return user


def get_user(path: Path, user_id: int) -> sqlite3.Row | None:
    with closing(connect(path)) as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def set_active(path: Path, username: str, active: bool) -> None:
    with closing(connect(path)) as conn, conn:
        conn.execute("UPDATE users SET active = ? WHERE username = ?",
                     (int(active), username))


def seed_demo_accounts(path: Path, *, admin_password: str,
                       editor_password: str) -> None:
    """Create the demo Admin and Editor if they do not exist yet."""
    demo = [
        ("admin", admin_password, "admin", "ASA Leadership"),
        ("editor", editor_password, "editor", "ASA Events Team"),
    ]
    for username, password, role, display_name in demo:
        try:
            create_account(path, username=username, password=password, role=role,
                           display_name=display_name)
        except UsernameTaken:
            pass
