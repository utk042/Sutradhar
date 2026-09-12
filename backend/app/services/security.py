"""Password hashing and JWT issuing/verification.

Passwords use Argon2id via argon2-cffi, the current recommendation for new
systems. Tokens are short-lived and carry the role as a claim, but the role is
always re-read from the database on each request — see app/api/deps.py. The
claim is a hint for the client, never an authorisation decision.
"""

from datetime import timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings
from app.models.types import utcnow

_hasher = PasswordHasher()

TokenKind = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return False


def create_token(*, user_id: int, role: str, kind: TokenKind) -> str:
    settings = get_settings()
    minutes = (
        settings.access_token_minutes
        if kind == "access"
        else settings.refresh_token_minutes
    )
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "kind": kind,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class TokenError(Exception):
    """Raised for any invalid, expired or wrong-kind token."""


def decode_token(token: str, *, expect: TokenKind) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "kind"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    # An access token must never be accepted where a refresh token is required,
    # or the short access lifetime is meaningless.
    if payload.get("kind") != expect:
        raise TokenError(f"expected a {expect} token")
    return payload
