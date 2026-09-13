"""A head of department running their own office.

Every route here requires the dept_head role, re-read from the database, and
every one is confined to the caller's own department. Being a head is authority
within an office, not across offices — so a head of one department reaching for
another's officer or document gets the same answer as a stranger: not found.

Everything that changes anything is audited.
"""

import logging
from collections import Counter
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_dept_head
from app.api.scope import load_managed_user, load_visible_document, visible_users
from app.api.work import CHART_DAYS
from app.db.app import get_app_session
from app.models.audit import AuditLogEntry
from app.models.decision import Decision
from app.models.department import Department
from app.models.document import Document
from app.models.finding import Finding as FindingRow
from app.models.setting import LLM_PROVIDER_KEY, Setting
from app.models.types import utcnow
from app.models.user import User
from app.schemas.management import (
    AuditPage,
    AuditRowOut,
    CreateOfficer,
    DepartmentOut,
    DepartmentStats,
    OfficerOut,
    OfficerWithWorkload,
    ProviderSetting,
    Reassign,
    SetActive,
)
from app.schemas.work import DayCount, FindingTally
from app.services import audit
from app.services.security import hash_password

router = APIRouter(prefix="/department", tags=["department"])
logger = logging.getLogger(__name__)

HeadDep = Annotated[User, Depends(require_dept_head)]
SessionDep = Annotated[Session, Depends(get_app_session)]


@router.get("", response_model=DepartmentOut)
def my_department(user: HeadDep, session: SessionDep) -> DepartmentOut:
    return DepartmentOut.model_validate(session.get(Department, user.department_id))


# --------------------------------------------------------------------------
# The three numbers
# --------------------------------------------------------------------------


@router.get("/stats", response_model=DepartmentStats)
def stats(user: HeadDep, session: SessionDep) -> DepartmentStats:
    """Counts for this department only. Every query carries the department."""
    mine = Document.department_id == user.department_id
    since = utcnow() - timedelta(days=1)

    processed_today = session.scalar(
        select(func.count())
        .select_from(Document)
        .where(mine, Document.reviewed_at.is_not(None), Document.reviewed_at >= since)
    ) or 0

    # How long a file waited between arriving and being decided. Computed in
    # Python rather than SQL so it stays portable — no SQLite date functions.
    decided = session.execute(
        select(Document.uploaded_at, Document.reviewed_at).where(
            mine, Document.reviewed_at.is_not(None)
        )
    ).all()
    average_seconds = (
        sum((r - u).total_seconds() for u, r in decided) / len(decided) if decided else None
    )

    flags_raised = session.scalar(
        select(func.count())
        .select_from(FindingRow)
        .join(Document, Document.id == FindingRow.document_id)
        .where(mine, FindingRow.status != "verified")
    ) or 0

    pending_now = session.scalar(
        select(func.count()).select_from(Document).where(mine, Document.status == "pending_review")
    ) or 0

    officers = session.scalar(
        select(func.count()).select_from(User).where(User.department_id == user.department_id)
    ) or 0

    # The two charts. Same shapes as an officer's own screen, over the whole
    # department instead of one desk — see app/api/work.py for why both are
    # bucketed in Python rather than in dialect-specific SQL.
    window_start = (utcnow() - timedelta(days=CHART_DAYS - 1)).date()
    per_day = Counter(
        moment.date()
        for moment in session.scalars(
            select(Document.reviewed_at).where(mine, Document.reviewed_at.is_not(None))
        ).all()
        if moment.date() >= window_start
    )
    daily = [
        DayCount(
            day=window_start + timedelta(days=offset),
            decided=per_day.get(window_start + timedelta(days=offset), 0),
        )
        for offset in range(CHART_DAYS)
    ]

    tally = dict(
        session.execute(
            select(FindingRow.status, func.count())
            .join(Document, Document.id == FindingRow.document_id)
            .where(mine)
            .group_by(FindingRow.status)
        ).all()
    )

    return DepartmentStats(
        processed_today=processed_today,
        average_seconds=round(average_seconds, 1) if average_seconds is not None else None,
        flags_raised=flags_raised,
        pending_now=pending_now,
        officers=officers,
        daily=daily,
        findings=FindingTally(
            verified=tally.get("verified", 0),
            mismatch=tally.get("mismatch", 0),
            unverifiable=tally.get("unverifiable", 0),
        ),
    )


# --------------------------------------------------------------------------
# The roster
# --------------------------------------------------------------------------


@router.get("/officers", response_model=list[OfficerWithWorkload])
def list_officers(user: HeadDep, session: SessionDep) -> list[OfficerWithWorkload]:
    people = session.scalars(visible_users(user).order_by(User.full_name)).all()

    rows: list[OfficerWithWorkload] = []
    for person in people:
        pending = session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.assigned_to == person.id, Document.status == "pending_review")
        ) or 0
        decided = session.scalar(
            select(func.count())
            .select_from(Decision)
            .where(Decision.decided_by == person.id)
        ) or 0
        rows.append(
            OfficerWithWorkload(
                **OfficerOut.model_validate(person).model_dump(),
                pending=pending,
                decided=decided,
            )
        )
    return rows


@router.post("/officers", response_model=OfficerOut, status_code=status.HTTP_201_CREATED)
def create_officer(
    payload: CreateOfficer, user: HeadDep, session: SessionDep
) -> OfficerOut:
    """Provision a login for this office.

    Not self-registration: a head creates an account for someone who already
    works there, and tells them the password. There is no email in this system
    and no reset flow, which is why the password is set here.

    The new officer joins the head's own department; the department is not a
    parameter, so it cannot be pointed at another office.
    """
    clash = session.scalar(
        select(User).where(User.mobile_number == payload.mobile_number)
    )
    if clash is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="mobile_already_registered")

    officer = User(
        mobile_number=payload.mobile_number,
        full_name=payload.full_name,
        role="officer",
        department_id=user.department_id,
        password_hash=hash_password(payload.password),
        is_active=True,
        created_by=user.id,
    )
    session.add(officer)
    session.flush()

    audit.record(
        session,
        action="officer_created",
        actor_user_id=user.id,
        actor_role=user.role,
        detail={"officer_user_id": officer.id, "department_id": user.department_id},
    )
    session.commit()
    session.refresh(officer)
    logger.info("officer %s created by user %s", officer.id, user.id)
    return OfficerOut.model_validate(officer)


@router.post("/officers/{officer_id}/active", response_model=OfficerOut)
def set_active(
    officer_id: int, payload: SetActive, user: HeadDep, session: SessionDep
) -> OfficerOut:
    """Suspend or restore an officer's access.

    Nothing they did is removed: their decisions and audit rows stay, still
    attributed to them. The role guard re-reads `is_active` on every request, so
    a suspension takes effect on their next one rather than at token expiry.
    """
    officer = load_managed_user(session, user, officer_id)
    officer.is_active = payload.is_active

    audit.record(
        session,
        action="officer_activated" if payload.is_active else "officer_deactivated",
        actor_user_id=user.id,
        actor_role=user.role,
        detail={"officer_user_id": officer.id},
    )
    session.commit()
    session.refresh(officer)
    return OfficerOut.model_validate(officer)


# --------------------------------------------------------------------------
# The audit trail
# --------------------------------------------------------------------------


@router.get("/audit", response_model=AuditPage)
def department_audit(
    user: HeadDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditPage:
    """This department's audit trail.

    Rows about this department's documents, plus rows about its people that
    carry no document — an officer being created or suspended. Rows belonging to
    another department are not returned, so a head cannot read another office's
    history through this.
    """
    my_documents = select(Document.id).where(Document.department_id == user.department_id)
    my_people = select(User.id).where(User.department_id == user.department_id)

    mine = AuditLogEntry.document_id.in_(my_documents) | (
        AuditLogEntry.document_id.is_(None) & AuditLogEntry.actor_user_id.in_(my_people)
    )

    total = session.scalar(select(func.count()).select_from(AuditLogEntry).where(mine)) or 0
    rows = session.scalars(
        select(AuditLogEntry)
        .where(mine)
        .order_by(AuditLogEntry.sequence.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    # Verified over the whole log, not the slice: a chain is only meaningful
    # end to end, and a head asking "has this been tampered with" deserves the
    # real answer rather than one about the page they happen to be reading.
    intact, _ = audit.verify_chain(session)

    return AuditPage(
        rows=[AuditRowOut.model_validate(r) for r in rows],
        total=total,
        chain_intact=intact,
    )


# --------------------------------------------------------------------------
# Reassignment
# --------------------------------------------------------------------------


@router.post("/documents/{document_id}/assign", status_code=status.HTTP_200_OK)
def reassign(
    document_id: int, payload: Reassign, user: HeadDep, session: SessionDep
) -> dict:
    """Move a pending file to another officer's desk.

    Only a file still waiting for a decision: once decided, moving it would
    change who appears accountable for a decision they did not make. Both the
    document and the new officer must be in the head's own department.
    """
    document = load_visible_document(session, user, document_id)
    if document.status not in {"uploaded", "processing", "pending_review"}:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="document_already_decided")

    target = session.scalar(visible_users(user).where(User.id == payload.assigned_to))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if not target.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="officer_not_active")

    previous = document.assigned_to
    document.assigned_to = target.id

    audit.record(
        session,
        action="document_reassigned",
        actor_user_id=user.id,
        actor_role=user.role,
        document_id=document.id,
        detail={"from_user_id": previous, "to_user_id": target.id},
    )
    session.commit()
    return {"code": "reassigned"}


# --------------------------------------------------------------------------
# Which model runs the checks
# --------------------------------------------------------------------------


@router.get("/provider", response_model=ProviderSetting)
def get_provider_setting(user: HeadDep, session: SessionDep) -> ProviderSetting:
    from app.config import get_settings

    stored = session.scalar(select(Setting).where(Setting.key == LLM_PROVIDER_KEY))
    return ProviderSetting(provider=stored.value if stored else get_settings().llm_provider)


@router.post("/provider", response_model=ProviderSetting)
def set_provider_setting(
    payload: ProviderSetting, user: HeadDep, session: SessionDep
) -> ProviderSetting:
    """Choose where documents are read.

    `local` is what makes "citizen data never leaves our own servers" a switch
    rather than a slogan: with it selected, no request leaves the host.
    """
    if payload.provider not in {"gemini", "local"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="unknown_provider")

    stored = session.scalar(select(Setting).where(Setting.key == LLM_PROVIDER_KEY))
    if stored is None:
        stored = Setting(key=LLM_PROVIDER_KEY, value=payload.provider, updated_by=user.id)
        session.add(stored)
    else:
        stored.value = payload.provider
        stored.updated_by = user.id

    audit.record(
        session,
        action="provider_changed",
        actor_user_id=user.id,
        actor_role=user.role,
        detail={"provider": payload.provider},
    )
    session.commit()
    return ProviderSetting(provider=payload.provider)
