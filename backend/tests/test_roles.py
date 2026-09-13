"""Roles are read from the database, never from the token.

The token carries a role claim so the interface can render the right screen, but
it is never the authorisation decision. These tests forge that claim and confirm
the server ignores it, and they take a signed-in user's access away underneath
them to confirm it takes effect at once rather than when their token expires.
"""

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import require_dept_head, require_officer, require_role
from app.config import get_settings
from app.db.app import AppSessionLocal
from app.models.types import utcnow
from app.models.user import User
from app.services.security import create_token, decode_token
from tests.conftest import DEPT_HEAD_MOBILE, OFFICER_MOBILE, PASSWORD


def _user(role: str) -> User:
    with AppSessionLocal() as session:
        return session.scalars(select(User).where(User.role == role)).first()


def test_the_token_carries_the_role_but_the_database_decides(officer):
    """A forged dept_head claim does not make an officer a dept head."""
    settings = get_settings()
    officer_row = _user("officer")

    forged = jwt.encode(
        {
            "sub": str(officer_row.id),
            "role": "dept_head",          # a lie
            "kind": "access",
            "iat": utcnow(),
            "exp": utcnow().timestamp() + 900,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    officer.cookies.set("sutradhar_access", forged)

    response = officer.get("/api/auth/me")
    assert response.status_code == 200
    # The claim said dept_head; the answer comes from the row.
    assert response.json()["role"] == "officer"


def test_a_token_signed_with_the_wrong_key_is_refused(anonymous):
    bad = jwt.encode(
        {"sub": "1", "role": "officer", "kind": "access",
         "iat": utcnow(), "exp": utcnow().timestamp() + 900},
        "not-the-real-signing-key",
        algorithm="HS256",
    )
    anonymous.cookies.set("sutradhar_access", bad)
    assert anonymous.get("/api/auth/me").status_code == 401


def test_an_unsigned_token_is_refused(anonymous):
    """The 'none' algorithm attack."""
    unsigned = jwt.encode(
        {"sub": "1", "role": "dept_head", "kind": "access",
         "iat": utcnow(), "exp": utcnow().timestamp() + 900},
        key="",
        algorithm="none",
    )
    anonymous.cookies.set("sutradhar_access", unsigned)
    assert anonymous.get("/api/auth/me").status_code == 401


def test_deactivating_a_user_takes_effect_at_once(officer):
    """Not when their token expires — on their very next request."""
    assert officer.get("/api/auth/me").status_code == 200

    with AppSessionLocal() as session:
        row = session.scalars(select(User).where(User.role == "officer")).first()
        row.is_active = False
        session.commit()

    assert officer.get("/api/auth/me").status_code == 401


def test_a_demoted_user_loses_access_at_once(dept_head):
    """The guard re-reads the role, so a demotion applies immediately."""
    row = _user("dept_head")
    guard_before = require_dept_head(row)
    assert guard_before.role == "dept_head"

    with AppSessionLocal() as session:
        demoted = session.get(User, row.id)
        demoted.role = "officer"
        session.commit()
        refreshed = session.get(User, row.id)

        with pytest.raises(HTTPException) as raised:
            require_dept_head(refreshed)
        assert raised.value.status_code == 403
        assert raised.value.detail == "insufficient_role"


def test_the_officer_guard_admits_both_roles():
    """A section head can do anything an officer can."""
    assert require_officer(_user("officer")).role == "officer"
    assert require_officer(_user("dept_head")).role == "dept_head"


def test_the_dept_head_guard_excludes_officers():
    with pytest.raises(HTTPException) as raised:
        require_dept_head(_user("officer"))
    assert raised.value.status_code == 403


def test_a_guard_for_an_unknown_role_admits_nobody():
    guard = require_role("auditor")
    for role in ("officer", "dept_head"):
        with pytest.raises(HTTPException):
            guard(_user(role))


def test_an_access_token_cannot_be_used_to_refresh(officer):
    """Otherwise the short access lifetime would mean nothing."""
    access = officer.cookies.get("sutradhar_access")
    officer.cookies.set("sutradhar_refresh", access)
    response = officer.post("/api/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "session_expired"


def test_a_refresh_token_cannot_be_used_as_a_session(anonymous):
    row = _user("officer")
    refresh = create_token(user_id=row.id, role=row.role, kind="refresh")
    anonymous.cookies.set("sutradhar_access", refresh)
    assert anonymous.get("/api/auth/me").status_code == 401


def test_tokens_state_their_kind():
    row = _user("officer")
    access = decode_token(create_token(user_id=row.id, role=row.role, kind="access"),
                          expect="access")
    assert access["kind"] == "access"
    assert access["sub"] == str(row.id)


def test_uploading_requires_a_session(anonymous, sample_pdf):
    response = anonymous.post(
        "/api/documents", files={"file": ("c.pdf", sample_pdf, "application/pdf")}
    )
    assert response.status_code == 401


def test_reading_a_document_requires_a_session(anonymous, reviewed_document):
    assert anonymous.get(f"/api/documents/{reviewed_document}").status_code == 401
    assert anonymous.get(f"/api/documents/{reviewed_document}/file").status_code == 401
    assert anonymous.get(f"/api/documents/{reviewed_document}/events").status_code == 401


# --------------------------------------------------------------------------
# Saying which role you are signing in as
# --------------------------------------------------------------------------
#
# The sign-in screen asks the officer to pick a role. That pick is a claim, not
# a grant: it is compared with the role on the account and can only refuse a
# sign-in. These tests are the ones that would fail if somebody ever made it
# decide anything.


def test_declaring_your_own_role_signs_you_in(anonymous):
    response = anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": OFFICER_MOBILE,
            "password": PASSWORD,
            "role": "officer",
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "officer"


def test_declaring_a_role_you_do_not_hold_is_refused(anonymous):
    """The point of the whole feature: claiming a role does not confer it."""
    response = anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": OFFICER_MOBILE,
            "password": PASSWORD,
            "role": "dept_head",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "role_mismatch"
    # And nothing was signed in.
    assert not [c for c in anonymous.cookies if c.startswith("sutradhar")]
    assert anonymous.get("/api/auth/me").status_code == 401


def test_a_head_declaring_officer_is_refused_too(anonymous):
    """It narrows in both directions. A head is not an officer here — the field
    says who you are, not which screen you would like."""
    response = anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": DEPT_HEAD_MOBILE,
            "password": PASSWORD,
            "role": "officer",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "role_mismatch"


def test_the_declared_role_never_reaches_the_token(anonymous):
    """Even when it matches, the claim is not what is written down: the token's
    role comes from the user's row, and the guards re-read that row anyway."""
    import jwt

    from app.config import get_settings

    anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": DEPT_HEAD_MOBILE,
            "password": PASSWORD,
            "role": "dept_head",
        },
    )
    token = anonymous.cookies["sutradhar_access"]
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    assert claims["role"] == "dept_head"

    with AppSessionLocal() as session:
        stored = session.scalar(select(User).where(User.mobile_number == DEPT_HEAD_MOBILE))
        assert claims["role"] == stored.role


def test_a_wrong_password_never_reveals_the_role(anonymous):
    """The role check sits below the password check on purpose.

    Above it, this endpoint would answer "is this number a head of department?"
    to anyone who asked. Both a matching and a mismatching claim must give the
    same generic answer when the password is wrong.
    """
    matching = anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": DEPT_HEAD_MOBILE,
            "password": "not-the-password",
            "role": "dept_head",
        },
    )
    mismatching = anonymous.post(
        "/api/auth/login",
        json={
            "mobile_number": DEPT_HEAD_MOBILE,
            "password": "not-the-password",
            "role": "officer",
        },
    )
    assert matching.status_code == mismatching.status_code == 401
    assert matching.json()["detail"] == mismatching.json()["detail"] == "invalid_credentials"


def test_an_unknown_number_gives_nothing_away_either(anonymous):
    response = anonymous.post(
        "/api/auth/login",
        json={"mobile_number": "9999999999", "password": PASSWORD, "role": "dept_head"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_credentials"


def test_an_invented_role_is_rejected_before_anything_else(anonymous):
    """Not a 401 with a hint — a schema rejection. The field is a closed set."""
    response = anonymous.post(
        "/api/auth/login",
        json={"mobile_number": OFFICER_MOBILE, "password": PASSWORD, "role": "admin"},
    )
    assert response.status_code == 422


def test_omitting_the_role_still_signs_you_in(anonymous):
    """The field is optional, and leaving it out is not a way around anything:
    the role still comes from the account either way."""
    response = anonymous.post(
        "/api/auth/login",
        json={"mobile_number": OFFICER_MOBILE, "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "officer"
