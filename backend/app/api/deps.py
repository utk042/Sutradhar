"""Request dependencies: who is calling, and may they.

Two rules enforced here:

1. The JWT arrives only in an httpOnly cookie. There is no Authorization-header
   path, so a token cannot be lifted out of the page by injected script.
2. The role is re-read from the database on every request. The token's `role`
   claim is never the authorisation decision — a user demoted a minute ago is
   denied immediately rather than when their token happens to expire.
"""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.app import get_app_session
from app.models.user import User
from app.services.security import TokenError, decode_token

ACCESS_COOKIE = "sutradhar_access"
REFRESH_COOKIE = "sutradhar_refresh"

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not_authenticated",
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="insufficient_role",
)


def get_current_user(
    session: Annotated[Session, Depends(get_app_session)],
    sutradhar_access: Annotated[str | None, Cookie()] = None,
) -> User:
    if not sutradhar_access:
        raise _UNAUTHENTICATED
    try:
        payload = decode_token(sutradhar_access, expect="access")
    except TokenError:
        raise _UNAUTHENTICATED from None

    user = session.scalar(select(User).where(User.id == int(payload["sub"])))
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: str):
    """Dependency factory re-checking the role against the database row."""

    def _guard(user: CurrentUserDep) -> User:
        if user.role not in allowed:
            raise _FORBIDDEN
        return user

    return _guard


require_officer = require_role("officer", "dept_head")
require_dept_head = require_role("dept_head")
