"""The review gate.

This is the only code path in the system that moves a document to `approved` or
`rejected`. No agent, no background task, no other route writes
`Document.status` to a decision value — `run_checks_for_document` moves it as far
as `pending_review` and stops there, which is the gate.

Every decision here:
  - requires a valid session cookie (the dependency verifies the JWT),
  - re-reads the officer's role from the database rather than trusting the token,
  - refuses anything not currently in `pending_review`, so a document cannot be
    decided twice or decided before the checks have run,
  - requires a reason to reject, and an override note to approve over a blocking
    finding,
  - writes the decision, the officer's ID and the timestamp in one transaction,
    together with the audit row.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep, require_officer
from app.db.app import get_app_session
from app.models.document import Document
from app.models.finding import Finding as FindingRow
from app.models.types import utcnow
from app.models.user import User
from app.schemas.document import DocumentDetail, ReviewDecision
from app.services import audit

router = APIRouter(prefix="/documents", tags=["review"])
logger = logging.getLogger(__name__)


@router.post("/{document_id}/decision", response_model=DocumentDetail)
def decide(
    document_id: int,
    payload: ReviewDecision,
    user: Annotated[User, Depends(require_officer)],
    session: Annotated[Session, Depends(get_app_session)],
) -> DocumentDetail:
    from app.api.documents import _load_detail

    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document_not_found")

    # The gate: only a document whose checks have finished, and which nobody has
    # already decided, can be decided now.
    if document.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="document_not_awaiting_review")

    if payload.decision == "rejected" and not (payload.reason or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="reason_required")

    has_blocking = session.scalar(
        select(FindingRow.id)
        .where(FindingRow.document_id == document_id, FindingRow.severity == "blocking")
        .limit(1)
    )
    if (
        payload.decision == "approved"
        and has_blocking
        and not (payload.override_note or "").strip()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="override_note_required")

    document.status = payload.decision
    document.reviewed_by = user.id
    document.reviewed_at = utcnow()
    document.decision_reason = (payload.reason or "").strip() or None
    document.override_note = (payload.override_note or "").strip() or None

    audit.record(
        session,
        action="document_approved" if payload.decision == "approved" else "document_rejected",
        actor_user_id=user.id,
        actor_role=user.role,
        document_id=document.id,
        detail={
            "decision": payload.decision,
            "over_blocking": bool(has_blocking),
            "reason_given": bool(document.decision_reason),
        },
    )
    # One transaction: the decision and its audit row commit together, or
    # neither does.
    session.commit()

    logger.info(
        "document %s %s by user %s", document.id, payload.decision, user.id
    )
    return _load_detail(session, document_id)
