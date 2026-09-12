"""The append-only audit log.

Every row carries `prev_hash`, the SHA-256 of the row before it, and `row_hash`,
the SHA-256 of its own contents including that link. Altering or removing any
historical row breaks the chain from that point on, and `verify_chain` finds
where.

There is no update and no delete anywhere in this module or in any route.

`detail` carries document IDs and decisions only. Citizen names, dates of birth
and document numbers must never be written here — the log is exportable, and an
export must not become a leak.
"""

import hashlib
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLogEntry
from app.models.types import utcnow

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64

#: Keys that must never appear in an audit detail payload.
_FORBIDDEN_DETAIL_KEYS = {
    "full_name", "name", "date_of_birth", "dob", "father_name",
    "address", "mobile_number", "record_ref", "document_value", "reference_value",
}


def _row_hash(
    *, sequence: int, actor_user_id: int | None, action: str,
    document_id: int | None, detail_json: str, created_at: str, prev_hash: str,
) -> str:
    # A stable, ordered serialisation: the hash must not change because a dict
    # iterated differently.
    payload = json.dumps(
        {
            "sequence": sequence,
            "actor_user_id": actor_user_id,
            "action": action,
            "document_id": document_id,
            "detail": detail_json,
            "created_at": created_at,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record(
    session: Session,
    *,
    action: str,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    document_id: int | None = None,
    detail: dict | None = None,
) -> AuditLogEntry:
    """Append one row. The caller's transaction commits it."""
    detail = detail or {}
    leaked = _FORBIDDEN_DETAIL_KEYS.intersection(detail)
    if leaked:
        # A programming error, caught here rather than in a published export.
        raise ValueError(f"audit detail must not carry personal data: {sorted(leaked)}")

    last = session.scalar(select(AuditLogEntry).order_by(AuditLogEntry.sequence.desc()))
    sequence = (last.sequence + 1) if last else 1
    prev_hash = last.row_hash if last else GENESIS_HASH

    created_at = utcnow()
    detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
    entry = AuditLogEntry(
        sequence=sequence,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        document_id=document_id,
        detail_json=detail_json,
        created_at=created_at,
        prev_hash=prev_hash,
        row_hash=_row_hash(
            sequence=sequence,
            actor_user_id=actor_user_id,
            action=action,
            document_id=document_id,
            detail_json=detail_json,
            created_at=created_at.isoformat(),
            prev_hash=prev_hash,
        ),
    )
    session.add(entry)
    return entry


def verify_chain(session: Session) -> tuple[bool, int | None]:
    """Replay the chain. Returns (intact, first broken sequence)."""
    expected_prev = GENESIS_HASH
    rows = session.scalars(select(AuditLogEntry).order_by(AuditLogEntry.sequence)).all()
    for row in rows:
        if row.prev_hash != expected_prev:
            return False, row.sequence
        recomputed = _row_hash(
            sequence=row.sequence,
            actor_user_id=row.actor_user_id,
            action=row.action,
            document_id=row.document_id,
            detail_json=row.detail_json,
            created_at=row.created_at.isoformat(),
            prev_hash=row.prev_hash,
        )
        if recomputed != row.row_hash:
            return False, row.sequence
        expected_prev = row.row_hash
    return True, None


def count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AuditLogEntry)) or 0
