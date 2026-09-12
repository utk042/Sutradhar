"""Document and review schemas for the API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentSummary(BaseModel):
    """A row in the officer's pending list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_ref: str
    doc_type: str
    original_filename: str
    status: str
    uploaded_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent: str
    field: str
    status: str
    severity: str
    document_value: str | None
    reference_value: str | None
    reference_source: str
    explanation_en: str
    confidence: float


class CheckRunOut(BaseModel):
    """Exposed so the parallelism claim is checkable, not just asserted."""

    model_config = ConfigDict(from_attributes=True)

    agent_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None


class DocumentDetail(DocumentSummary):
    findings: list[FindingOut]
    checks: list[CheckRunOut]
    extracted: dict[str, str]
    #: The document's text, so the review screen can mark checked values in place.
    extracted_text: str | None = None
    #: True when at least one finding is blocking, so the screen can require an
    #: override note before approval.
    has_blocking: bool
    reviewed_at: datetime | None = None
    decision_reason: str | None = None
    #: The officer's justification for approving over a blocking finding. Shown
    #: back to them on the confirmation, because a note nobody sees again is not
    #: a record of anything.
    override_note: str | None = None


class ReviewDecision(BaseModel):
    """The officer's decision. The only thing that moves a document's status."""

    decision: Literal["approved", "rejected"]
    #: Required when rejecting.
    reason: str | None = Field(default=None, max_length=2000)
    #: Required when approving over a blocking finding.
    override_note: str | None = Field(default=None, max_length=2000)
