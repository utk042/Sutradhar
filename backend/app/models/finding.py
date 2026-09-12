from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import UTCDateTime, portable_enum, utcnow

AGENT_RUN_STATUSES = ("running", "succeeded", "failed")
AgentRunStatusEnum = portable_enum(*AGENT_RUN_STATUSES, name="agent_run_status")

FINDING_STATUSES = ("verified", "mismatch", "unverifiable")
FindingStatusEnum = portable_enum(*FINDING_STATUSES, name="finding_status")

FINDING_SEVERITIES = ("info", "warning", "blocking")
FindingSeverityEnum = portable_enum(*FINDING_SEVERITIES, name="finding_severity")


class AgentRun(Base):
    """One specialist check's execution window.

    `duration_ms` alongside `started_at` is what makes the parallelism claim
    provable: three overlapping windows whose total wall time is the slowest
    check, not the sum of all three.
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(AgentRunStatusEnum, default="running")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    findings: Mapped[list["Finding"]] = relationship(back_populates="agent_run")


class Finding(Base):
    """One check result about one field, with the evidence behind it.

    Mirrors the Finding Pydantic schema the agents return. `unverifiable` is a
    first-class status, not an error: when the system cannot tell a
    transliteration variant from a discrepancy it says so and the officer
    decides.
    """

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    agent_run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"))

    agent: Mapped[str] = mapped_column(String(64))
    field: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(FindingStatusEnum)
    severity: Mapped[str] = mapped_column(FindingSeverityEnum, default="info")

    document_value: Mapped[str | None] = mapped_column(Text, default=None)
    reference_value: Mapped[str | None] = mapped_column(Text, default=None)
    # Cited on screen beside the values, e.g. "registry_records #4471".
    reference_source: Mapped[str] = mapped_column(String(255))

    explanation_en: Mapped[str] = mapped_column(Text)
    explanation_hi: Mapped[str | None] = mapped_column(Text, default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    agent_run: Mapped[AgentRun] = relationship(back_populates="findings")
