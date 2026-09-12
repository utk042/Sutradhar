"""Sign-in, refresh and sign-out.

Tokens are set as httpOnly, SameSite=Strict cookies and never returned in a
response body.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ACCESS_COOKIE, REFRESH_COOKIE, CurrentUserDep
from app.config import get_settings
from app.db.app import get_app_session
from app.models.user import User
from app.schemas.auth import CurrentUser, LoginRequest, MessageResponse
from app.services.security import (
    TokenError,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _set_auth_cookies(response: Response, *, user: User) -> None:
    settings = get_settings()
    common = {
        "httponly": True,
        "samesite": "strict",
        "secure": settings.cookie_secure,
        "domain": settings.cookie_domain,
    }
    response.set_cookie(
        ACCESS_COOKIE,
        create_token(user_id=user.id, role=user.role, kind="access"),
        max_age=settings.access_token_minutes * 60,
        path="/",
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_token(user_id=user.id, role=user.role, kind="refresh"),
        max_age=settings.refresh_token_minutes * 60,
        # Scoped to the refresh route alone, so the long-lived credential is not
        # attached to every ordinary request.
        path="/api/auth/refresh",
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth/refresh")


@router.post("/login", response_model=CurrentUser)
def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_app_session)],
) -> CurrentUser:
    user = session.scalar(select(User).where(User.mobile_number == payload.mobile_number))

    # One response for "no such user", "wrong password" and "deactivated", so the
    # endpoint cannot be used to discover which mobile numbers are registered.
    # Verify against a dummy hash when the user is absent to keep the timing
    # comparable.
    password_ok = (
        verify_password(payload.password, user.password_hash)
        if user is not None
        else verify_password(payload.password, _DUMMY_HASH)
    )
    if user is None or not password_ok or not user.is_active:
        # Log the attempt without the mobile number: application logs must never
        # carry citizen or officer identifiers.
        logger.info("login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    # Transparently upgrade a hash whose cost parameters are now out of date.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        session.commit()

    _set_auth_cookies(response, user=user)
    logger.info("login_succeeded user_id=%s", user.id)
    return CurrentUser.model_validate(user)


@router.post("/refresh", response_model=CurrentUser)
def refresh(
    response: Response,
    session: Annotated[Session, Depends(get_app_session)],
    sutradhar_refresh: Annotated[str | None, Cookie()] = None,
) -> CurrentUser:
    if not sutradhar_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    try:
        payload = decode_token(sutradhar_refresh, expect="refresh")
    except TokenError:
        _clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session_expired") from None

    user = session.scalar(select(User).where(User.id == int(payload["sub"])))
    if user is None or not user.is_active:
        _clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    _set_auth_cookies(response, user=user)
    return CurrentUser.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    _clear_auth_cookies(response)
    return MessageResponse(code="signed_out")


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUserDep) -> CurrentUser:
    return CurrentUser.model_validate(user)


# Argon2 hash of a value no one can supply, used only to equalise timing on the
# "unknown mobile number" path above.
_DUMMY_HASH = hash_password("sutradhar-timing-equaliser")
