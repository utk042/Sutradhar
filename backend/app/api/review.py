"""The review gate.

This is the only module in the system that writes a decision onto a document.
Two routes do it:

- An officer decides a document their office has finished checking.
- A head of department supersedes a decision already made in their office.

A supersede is not an edit. The original decision stays, attributed to whoever
made it, and both appear in the history and the audit log. What changes is which
decision is in force.

Every path here:
  - requires a valid session cookie,
  - re-reads the role from the database rather than trusting the token,
  - is scoped to the caller's own department, so a head of one office cannot
    reach into another's,
  - requires a reason to reject and to supersede anything, and an override note
    to approve over a blocking finding,
  - writes the decision and its audit row in one transaction.

`tests/test_review_gate.py` asserts by reading the syntax tree that no other
module in the application assigns a decision to a document's status.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_dept_head, require_officer
from app.api.scope import load_visible_document
from app.db.app import get_app_session
from app.models.finding import Finding as FindingRow
from app.models.user import User
from app.schemas.document import DocumentDetail, ReviewDecision, SupersedeDecision
from app.services import audit
from app.services.decisions import current_decision, record_decision

router = APIRouter(prefix="/documents", tags=["review"])
logger = logging.getLogger(__name__)


def _has_blocking(session: Session, document_id: int) -> bool:
    return session.scalar(
        select(FindingRow.id)
        .where(FindingRow.document_id == document_id, FindingRow.severity == "blocking")
        .limit(1)
    ) is not None


@router.post("/{document_id}/decision", response_model=DocumentDetail)
def decide(
    document_id: int,
    payload: ReviewDecision,
    user: Annotated[User, Depends(require_officer)],
    session: Annotated[Session, Depends(get_app_session)],
) -> DocumentDetail:
    from app.api.documents import _load_detail

    document = load_visible_document(session, user, document_id)

    # The gate: only a document whose checks have finished, and which nobody has
    # already decided, can be decided now.
    if document.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="document_not_awaiting_review")

    if payload.decision == "rejected" and not (payload.reason or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="reason_required")

    blocking = _has_blocking(session, document_id)
    if (
        payload.decision == "approved"
        and blocking
        and not (payload.override_note or "").strip()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="override_note_required")

    record_decision(
        session,
        document=document,
        actor=user,
        decision=payload.decision,
        reason=payload.reason,
        override_note=payload.override_note,
    )

    audit.record(
        session,
        action="document_approved" if payload.decision == "approved" else "document_rejected",
        actor_user_id=user.id,
        actor_role=user.role,
        document_id=document.id,
        detail={
            "decision": payload.decision,
            "over_blocking": blocking,
            "reason_given": bool((payload.reason or "").strip()),
        },
    )
    # One transaction: the decision and its audit row commit together, or
    # neither does.
    session.commit()
    return _load_detail(session, user, document_id)


@router.post("/{document_id}/supersede", response_model=DocumentDetail)
def supersede(
    document_id: int,
    payload: SupersedeDecision,
    user: Annotated[User, Depends(require_dept_head)],
    session: Annotated[Session, Depends(get_app_session)],
) -> DocumentDetail:
    """A head of department replaces a decision made in their office.

    The earlier decision is not rewritten — it is marked as superseded by this
    one, and stays visible and attributed. A reason is always required: this
    overrules a colleague, and the record should say why.
    """
    from app.api.documents import _load_detail

    document = load_visible_document(session, user, document_id)

    existing = current_decision(session, document_id)
    if existing is None or document.status not in {"approved", "rejected"}:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="document_not_decided")

    if not (payload.reason or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="reason_required")

    if payload.decision == existing.decision:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="decision_unchanged")

    if (
        payload.decision == "approved"
        and _has_blocking(session, document_id)
        and not (payload.override_note or "").strip()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="override_note_required")

    record_decision(
        session,
        document=document,
        actor=user,
        decision=payload.decision,
        reason=payload.reason,
        override_note=payload.override_note,
        supersedes=existing,
    )

    audit.record(
        session,
        action="decision_superseded",
        actor_user_id=user.id,
        actor_role=user.role,
        document_id=document.id,
        detail={
            "decision": payload.decision,
            "replaced_decision_id": existing.id,
            "originally_decided_by": existing.decided_by,
        },
    )
    session.commit()
    return _load_detail(session, user, document_id)
