"""An officer's own work, counted.

The head of department has an office-wide screen in `management.py`. This is the
same idea one desk down: what is waiting for *this* officer, what they have
decided, and how long they take. Nothing here is office-wide and nothing here is
about anybody else — an officer sees their own caseload and no colleague's.

That narrowing is not written out here. Every query goes through
`scope.visible_documents`, which already means "assigned to me, in my
department" for an officer and "my whole department" for a head. One definition
of who may see what, used by every route that reaches a document —
`tests/test_department_scope.py` asserts this module does exactly that.

Read-only. Nothing on this route writes anything.
"""

from collections import Counter
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_officer
from app.api.scope import visible_documents
from app.db.app import get_app_session
from app.models.document import Document
from app.models.finding import Finding as FindingRow
from app.models.types import utcnow
from app.models.user import User
from app.schemas.work import DayCount, DecidedDocument, FindingTally, WorkSummary

router = APIRouter(prefix="/work", tags=["work"])

OfficerDep = Annotated[User, Depends(require_officer)]
SessionDep = Annotated[Session, Depends(get_app_session)]

#: How many recent decisions the screen shows. Enough to recognise this week's
#: work, short enough that the page needs no pagination of its own.
RECENT_LIMIT = 10

#: The window the day-by-day chart covers. A week reads as a week to the person
#: looking at it, and seven columns fit a phone without crowding.
CHART_DAYS = 7


@router.get("", response_model=WorkSummary)
def my_work(user: OfficerDep, session: SessionDep) -> WorkSummary:
    mine = visible_documents(user).with_only_columns(Document.id)
    since = utcnow() - timedelta(days=1)

    pending_now = session.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.id.in_(mine), Document.status == "pending_review")
    ) or 0

    decided_today = session.scalar(
        select(func.count())
        .select_from(Document)
        .where(
            Document.id.in_(mine),
            Document.reviewed_by == user.id,
            Document.reviewed_at.is_not(None),
            Document.reviewed_at >= since,
        )
    ) or 0

    decided_total = session.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.id.in_(mine), Document.reviewed_by == user.id)
    ) or 0

    # How long each file waited between arriving and being decided. Averaged in
    # Python rather than SQL so it stays portable to Postgres unchanged — no
    # SQLite date arithmetic anywhere.
    windows = session.execute(
        select(Document.uploaded_at, Document.reviewed_at).where(
            Document.id.in_(mine),
            Document.reviewed_by == user.id,
            Document.reviewed_at.is_not(None),
        )
    ).all()
    average_seconds = (
        sum((decided - arrived).total_seconds() for arrived, decided in windows) / len(windows)
        if windows
        else None
    )

    # Only what is still waiting. A count of everything the checks have ever
    # flagged is a number an officer can do nothing about; a count of what is
    # flagged on files still on their desk is the morning's work.
    flags_waiting = session.scalar(
        select(func.count())
        .select_from(FindingRow)
        .join(Document, Document.id == FindingRow.document_id)
        .where(
            Document.id.in_(mine),
            Document.status == "pending_review",
            FindingRow.status != "verified",
        )
    ) or 0

    # Day by day, for the chart. Bucketed in Python rather than SQL: date
    # truncation is dialect-specific — `date()` in SQLite, `date_trunc` in
    # Postgres — and nothing here is big enough for that to matter. Everything
    # else in this project stays portable the same way.
    window_start = (utcnow() - timedelta(days=CHART_DAYS - 1)).date()
    decided_days = session.scalars(
        select(Document.reviewed_at).where(
            Document.id.in_(mine),
            Document.reviewed_by == user.id,
            Document.reviewed_at.is_not(None),
        )
    ).all()
    per_day = Counter(
        moment.date() for moment in decided_days if moment.date() >= window_start
    )
    # Every day in the window, including the empty ones: a chart that drops the
    # quiet days misstates the shape of the week.
    daily = [
        DayCount(day=window_start + timedelta(days=offset), decided=per_day.get(window_start + timedelta(days=offset), 0))
        for offset in range(CHART_DAYS)
    ]

    # How the checks came out across everything in view, for the status bars.
    tally = dict(
        session.execute(
            select(FindingRow.status, func.count())
            .join(Document, Document.id == FindingRow.document_id)
            .where(Document.id.in_(mine))
            .group_by(FindingRow.status)
        ).all()
    )
    findings = FindingTally(
        verified=tally.get("verified", 0),
        mismatch=tally.get("mismatch", 0),
        unverifiable=tally.get("unverifiable", 0),
    )

    recent = session.scalars(
        visible_documents(user)
        .where(Document.reviewed_by == user.id, Document.reviewed_at.is_not(None))
        .order_by(Document.reviewed_at.desc())
        .limit(RECENT_LIMIT)
    ).all()

    return WorkSummary(
        pending_now=pending_now,
        decided_today=decided_today,
        decided_total=decided_total,
        average_seconds=round(average_seconds, 1) if average_seconds is not None else None,
        flags_waiting=flags_waiting,
        daily=daily,
        findings=findings,
        recent=[DecidedDocument.model_validate(d) for d in recent],
    )
