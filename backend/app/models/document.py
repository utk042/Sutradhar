from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import UTCDateTime, portable_enum, utcnow

DOCUMENT_STATUSES = (
    "uploaded",
    "processing",
    "pending_review",
    "approved",
    "rejected",
    "failed",
)
DocumentStatusEnum = portable_enum(*DOCUMENT_STATUSES, name="document_status")

DOCUMENT_TYPES = (
    "birth_certificate",
    "income_certificate",
    "scheme_application",
    "unknown",
)
DocumentTypeEnum = portable_enum(*DOCUMENT_TYPES, name="document_type")


class Document(Base):
    """An uploaded citizen document and its decision state.

    Only app/api/review.py moves `status` to approved or rejected. No agent,
    background task or other route writes this column.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Shown in the interface and written to the audit log, so that no screen or
    # log line needs to expose a citizen's name to identify a file.
    public_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(DocumentTypeEnum, default="unknown")

    original_filename: Mapped[str] = mapped_column(String(255))
    # Generated name on disk. Never built from user input, never echoed back as
    # a path — see app/services/storage.py.
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)

    status: Mapped[str] = mapped_column(DocumentStatusEnum, default="uploaded", index=True)

    #: The text read off the document, kept so the review screen can show the
    #: document with each checked value marked in place. No new exposure: this is
    #: the same content as the stored file, which is already held.
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)

    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    #: Taken from the uploader at creation. Kept on the row rather than joined
    #: through the uploader, so a document cannot change department when a person
    #: moves office, and so every scoped query is a single predicate.
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    #: The officer responsible for deciding it. Starts as the uploader and can be
    #: reassigned by a head of department.
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    # Required when rejecting; the review endpoint enforces it.
    decision_reason: Mapped[str | None] = mapped_column(Text, default=None)
    # Required to approve over a blocking finding.
    override_note: Mapped[str | None] = mapped_column(Text, default=None)

    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Document id={self.id} ref={self.public_ref} status={self.status}>"


class ExtractedField(Base):
    """One field read off the document by OCR."""

    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(64))
    field_value: Mapped[str | None] = mapped_column(Text, default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="extracted_fields")
