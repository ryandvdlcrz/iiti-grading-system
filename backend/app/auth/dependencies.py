"""
Auth for every route.

The login page (POST /auth/login) hands the browser a signed token. Routes read
it from the `Authorization: Bearer <token>` header here, so the rest of the app
keeps depending on get_current_teacher() and nothing else has to change.

TEMPORARY: while ALLOW_PLACEHOLDER_AUTH=true in .env, a request that sends NO
token but does send the old X-Teacher-Id header is still accepted (as a plain
teacher). That keeps pages that haven't been switched to the token yet working.
Set ALLOW_PLACEHOLDER_AUTH=false once every page sends the token -- until then
anyone can claim to be any teacher by sending that header.

A token that is present but bad or expired is always rejected; it never falls
back to the placeholder header.
"""

import jwt  # PyJWT
from fastapi import Depends, Header, HTTPException

from app.config import settings

ADMIN_ROLES = {"Admin", "SuperAdmin"}


class CurrentTeacher:
    def __init__(self, teacher_id: str | None, role: str = "Teacher", user_id: str | None = None):
        # teacher_id is the professor id (same value as profId in schedules.classes).
        # It is None for admin accounts, which aren't linked to a professor.
        self.teacher_id = teacher_id
        self.role = role
        self.user_id = user_id


def _decode_token(token: str) -> dict:
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY is not set in .env.")
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid login token. Please log in again.")


def get_current_teacher(
    authorization: str | None = Header(default=None),
    x_teacher_id: str | None = Header(default=None),
) -> CurrentTeacher:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Invalid Authorization header.")
        payload = _decode_token(token.strip())
        return CurrentTeacher(
            teacher_id=payload.get("professor_id"),
            role=payload.get("role", ""),
            user_id=payload.get("sub"),
        )

    if settings.ALLOW_PLACEHOLDER_AUTH and x_teacher_id:
        return CurrentTeacher(teacher_id=x_teacher_id, role="Teacher")

    raise HTTPException(status_code=401, detail="Not logged in.")


def get_current_admin(current: CurrentTeacher = Depends(get_current_teacher)) -> CurrentTeacher:
    """Same as get_current_teacher, but only lets Admin / SuperAdmin tokens through.
    The placeholder header never counts as admin."""
    if current.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current