"""
PLACEHOLDER AUTH.

The login/session system is owned by another team (Node.js side). Once they
confirm how identity is passed to this service (JWT in a header? a shared
session/cookie looked up in MongoDB? something else?), this file is the
ONLY place that needs to change — every route already depends on
`get_current_teacher()` instead of reading headers/cookies directly.

Current behavior (temporary):
    Reads a plain `X-Teacher-Id` header and trusts it as-is. NOT secure —
    anyone can send any teacher id. Fine for local development only.

TODO once the other team answers:
  - If JWT: verify signature with their shared secret, extract teacher id
    from the token's claims.
  - If session/cookie: look up the session in MongoDB (probably in a
    `sessions` collection) and resolve it to a teacher id.
"""

from fastapi import Header, HTTPException


class CurrentTeacher:
    def __init__(self, teacher_id: str):
        self.teacher_id = teacher_id


def get_current_teacher(x_teacher_id: str | None = Header(default=None)) -> CurrentTeacher:
    if not x_teacher_id:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Teacher-Id header (placeholder auth — replace once real auth mechanism is confirmed).",
        )
    return CurrentTeacher(teacher_id=x_teacher_id)