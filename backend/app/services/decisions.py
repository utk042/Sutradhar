"""Recording decisions.

A decision is never edited. An officer's decision is a row; a head of
department superseding it is another row, with the first marked as superseded
by the second. Both stay, both attributed, and the audit log holds both.

`Document.status` and its decision fields are kept in step with whichever
decision is currently in force, so every existing query and screen keeps
working — but this table is the record, and the columns on the document are a
convenience derived from it.

This module does not decide who may do any of it. That is the route's job, and
keeping it there is what lets the structural test assert that only one module
writes a decision.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.document import Document
from app.models.types import utcnow
from app.models.user import User

logger = logging.getLogger(__name__)


def current_decision(session: Session, document_id: int) -> Decision | None:
    """The decision in force: the newest one nothing has superseded."""
    return session.scalar(
        select(Decision)
        .where(Decision.document_id == document_id, Decision.superseded_by.is_(None))
        .order_by(Decision.created_at.desc(), Decision.id.desc())
    )


def decision_history(session: Session, document_id: int) -> list[Decision]:
    """Every decision ever made on this document, oldest first."""
    return list(
        session.scalars(
            select(Decision)
            .where(Decision.document_id == document_id)
            .order_by(Decision.created_at, Decision.id)
        ).all()
    )


def record_decision(
    session: Session,
    *,
    document: Document,
    actor: User,
    decision: str,
    reason: str | None = None,
    override_note: str | None = None,
    supersedes: Decision | None = None,
) -> Decision:
    """Write a decision, and bring the document into line with it.

    The caller commits. Nothing here checks permission — see the module note.
    """
    row = Decision(
        document_id=document.id,
        decided_by=actor.id,
        # The role as held at the time, so the record still reads correctly
        # after somebody is promoted or moves office.
        decided_as=actor.role,
        decision=decision,
        reason=(reason or "").strip() or None,
        override_note=(override_note or "").strip() or None,
    )
    session.add(row)
    session.flush()

    if supersedes is not None:
        # The earlier decision is marked, never rewritten: its own fields are
        # untouched and it stays attributed to whoever made it.
        supersedes.superseded_by = row.id

    document.status = decision
    document.reviewed_by = actor.id
    document.reviewed_at = row.created_at
    document.decision_reason = row.reason
    document.override_note = row.override_note

    logger.info(
        "document %s %s by user %s%s",
        document.id,
        decision,
        actor.id,
        f" superseding decision {supersedes.id}" if supersedes else "",
    )
    return row
