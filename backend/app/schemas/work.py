"""What an officer's own screen shows.

No citizen name, date of birth or document number appears here — only the public
reference, which is what every other screen and every audit row uses to name a
file.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DecidedDocument(BaseModel):
    """One file this officer has already decided."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_ref: str
    #: "approved" or "rejected" — the document's status once it has been decided.
    status: str
    reviewed_at: datetime | None


class WorkSummary(BaseModel):
    """The numbers on an officer's own screen, and what they have just done."""

    #: Files on this officer's desk waiting for a decision right now.
    pending_now: int
    #: Decisions this officer made in the last twenty-four hours.
    decided_today: int
    #: Every decision this officer has ever made.
    decided_total: int
    #: Mean seconds between a file arriving and this officer deciding it.
    average_seconds: float | None
    #: Findings needing attention on files still waiting — the morning's work,
    #: rather than a lifetime total nothing can be done about.
    flags_waiting: int
    recent: list[DecidedDocument]
