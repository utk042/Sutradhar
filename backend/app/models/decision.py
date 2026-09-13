"""The history of decisions on a document.

A decision is never edited. When a head of department supersedes an officer's
decision, that is a new row: the original stays, attributed to the officer who
made it, and the audit log holds both.

`Document.status` is the current answer; this table is how it got there. The
newest row that has not itself been superseded is the one in force.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import UTCDateTime, portable_enum, utcnow

DECISION_VALUES = ("approved", "rejected")
DecisionEnum = portable_enum(*DECISION_VALUES, name="decision_value")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    #: The role the decider held at the time, so the record still reads correctly
    #: after someone is promoted or moved.
    decided_as: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(DecisionEnum)

    #: Required when rejecting, and when superseding anything.
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    #: Required to approve over a blocking finding.
    override_note: Mapped[str | None] = mapped_column(Text, default=None)

    #: Set when a later decision replaces this one. The row itself never changes
    #: otherwise, and is never deleted.
    superseded_by: Mapped[int | None] = mapped_column(
        ForeignKey("decisions.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
