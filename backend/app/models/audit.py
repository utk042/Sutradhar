"""Append-only audit log with a tamper-evident hash chain.

Every row carries `prev_hash` (the preceding row's `row_hash`) and its own
`row_hash`. Altering or deleting any historical row breaks the chain from that
point onward, which `app/services/audit.py` can detect by replaying it.

There is no update or delete route for this table anywhere in the application.

`detail_json` carries document IDs and decisions only. Citizen names, dates of
birth and document numbers must never be written here — the audit log is
exportable, and an export must not become a data leak.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import UTCDateTime, utcnow

AUDIT_ACTIONS = (
    "document_uploaded",
    "checks_started",
    "checks_completed",
    "document_approved",
    "document_rejected",
    "decision_superseded",
    "officer_created",
    "officer_activated",
    "officer_deactivated",
    "document_reassigned",
    "provider_changed",
)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    actor_role: Mapped[str | None] = mapped_column(String(32), default=None)
    action: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), default=None, index=True
    )
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    # Genesis row carries 64 zeroes.
    prev_hash: Mapped[str] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64), unique=True)

    sequence: Mapped[int] = mapped_column(Integer, unique=True)
