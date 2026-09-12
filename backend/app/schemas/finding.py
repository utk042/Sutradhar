"""What a check returns.

Agents produce these and nothing else. They hold no database session and never
persist anything — the application layer writes them. That is what keeps "the
system can read, never write" true of the system's own bookkeeping, not just of
the citizen's records.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FindingStatus = Literal["verified", "mismatch", "unverifiable"]
FindingSeverity = Literal["info", "warning", "blocking"]


class Finding(BaseModel):
    """One observation about one field, with the evidence behind it."""

    model_config = ConfigDict(frozen=True)

    agent: str
    field: str
    status: FindingStatus
    severity: FindingSeverity = "info"
    document_value: str | None = None
    reference_value: str | None = None
    #: Cited on screen beside the values, e.g. "registry_records #BC-4471".
    reference_source: str
    #: Plain language, for an officer. No jargon, no field names, no codes.
    explanation_en: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class CheckResult(BaseModel):
    """One check's output, with the timing that proves how it ran.

    `started_at` is captured by the check itself, not by whatever stores it
    later. That is the point: three checks starting at the same instant and
    finishing at different ones is what shows they ran together, and a start time
    stamped at insert would show nothing at all.
    """

    agent: str
    findings: list[Finding]
    started_at: datetime
    duration_ms: int
    failed: bool = False
    error_message: str | None = None

    @property
    def finished_at(self) -> datetime:
        from datetime import timedelta

        return self.started_at + timedelta(milliseconds=self.duration_ms)
