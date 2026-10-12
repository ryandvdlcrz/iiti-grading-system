"""
Login for the grading system.

POST /auth/login  -> checks "user or email" + password against the shared
`users` collection (bcrypt, the same hashes the other system uses) and returns
a signed token plus basic user info.

Read-only: nothing in `users` is written or changed by logging in.
The token is not enforced by the other routes yet (they still use the
placeholder X-Teacher-Id header) -- that is the next phase.
"""

import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt  # this is the PyJWT package: pip install PyJWT
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# Roles allowed to log in here. Remove "Admin" and "SuperAdmin" to make this
# page teachers-only.
ALLOWED_ROLES = {"Teacher", "Admin", "SuperAdmin"}

# Compared against when the account doesn't exist, so a wrong username takes
# about as long to reject as a wrong password.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=12))


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)  # username or email
    password: str = Field(min_length=1, max_length=128)


class LoginUser(BaseModel):
    id: str
    name: str
    email: str
    role: str
    institute: str
    professor_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: LoginUser


def _find_user(db, identifier: str) -> dict | None:
    """Email match first, then username. Case-insensitive. If more than one
    account matches, treat it as not found rather than guessing."""
    ident = identifier.strip()
    exact_ci = {"$regex": f"^{re.escape(ident)}$", "$options": "i"}

    by_email = list(db.users.find({"email": exact_ci}).limit(2))
    if len(by_email) == 1:
        return by_email[0]
    if len(by_email) > 1:
        return None

    by_username = list(db.users.find({"username": exact_ci}).limit(2))
    if len(by_username) == 1:
        return by_username[0]
    return None


def _password_ok(password: str, stored_hash: str | None) -> bool:
    try:
        target = stored_hash.encode("utf-8") if stored_hash else _DUMMY_HASH
        matches = bcrypt.checkpw(password.encode("utf-8"), target)
    except ValueError:
        # Password longer than 72 bytes, or a stored value that isn't a bcrypt hash.
        return False
    return bool(stored_hash) and matches


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if settings.USE_MOCK_DATA:
        raise HTTPException(
            status_code=503,
            detail="Login needs the real database. Set USE_MOCK_DATA=false in .env.",
        )
    if not settings.SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY is not set in .env.")

    db = get_db()
    user = _find_user(db, payload.identifier)
    password_ok = _password_ok(payload.password, user.get("password") if user else None)

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Incorrect user/email or password.")

    role = user.get("role", "")
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="This account can't log in here.")

    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": str(user["_id"]),
            "role": role,
            "professor_id": user.get("professorId"),
            "exp": expires,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return LoginResponse(
        access_token=token,
        user=LoginUser(
            id=str(user["_id"]),
            name=user.get("username", ""),
            email=user.get("email", ""),
            role=role,
            institute=user.get("institute", ""),
            professor_id=user.get("professorId"),
        ),
    )