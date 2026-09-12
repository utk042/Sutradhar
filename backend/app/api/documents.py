"""Upload, list and inspect documents.

None of these routes change a document's decision. Only app/api/review.py does.
"""

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep
from app.db.app import AppSessionLocal, get_app_session
from app.models.document import Document, ExtractedField
from app.models.finding import AgentRun, Finding as FindingRow
from app.schemas.document import CheckRunOut, DocumentDetail, DocumentSummary, FindingOut
from app.services import audit, storage
from app.services.review import run_checks_for_document

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


async def _run_checks(document_id: int) -> None:
    """Background task. Opens its own session — the request's is long gone."""
    with AppSessionLocal() as session:
        document = session.get(Document, document_id)
        if document is None:
            return
        try:
            await run_checks_for_document(session, document)
        except Exception:
            logger.exception("background checks failed for document %s", document_id)


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload(
    user: CurrentUserDep,
    background: BackgroundTasks,
    session: Annotated[Session, Depends(get_app_session)],
    file: UploadFile,
) -> DocumentSummary:
    data = await file.read()
    try:
        stored = storage.store_upload(data=data, filename=file.filename)
    except storage.UploadRejected as exc:
        # A code, not a sentence: the screen renders it from its locale file.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.code) from None

    document = Document(
        public_ref=f"DOC-{secrets.token_hex(4).upper()}",
        doc_type="unknown",
        original_filename=stored.original_filename,
        stored_filename=stored.stored_filename,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status="uploaded",
        uploaded_by=user.id,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    audit.record(
        session,
        action="document_uploaded",
        actor_user_id=user.id,
        actor_role=user.role,
        document_id=document.id,
        detail={"mime_type": stored.mime_type, "size_bytes": stored.size_bytes},
    )
    session.commit()

    logger.info("document %s uploaded by user %s", document.id, user.id)
    background.add_task(_run_checks, document.id)
    return DocumentSummary.model_validate(document)


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    user: CurrentUserDep,
    session: Annotated[Session, Depends(get_app_session)],
) -> list[DocumentSummary]:
    rows = session.scalars(
        select(Document).order_by(Document.uploaded_at.desc()).limit(100)
    ).all()
    return [DocumentSummary.model_validate(r) for r in rows]


def _load_detail(session: Session, document_id: int) -> DocumentDetail:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document_not_found")

    findings = session.scalars(
        select(FindingRow).where(FindingRow.document_id == document_id).order_by(FindingRow.id)
    ).all()
    checks = session.scalars(
        select(AgentRun).where(AgentRun.document_id == document_id).order_by(AgentRun.id)
    ).all()
    extracted_rows = session.scalars(
        select(ExtractedField).where(ExtractedField.document_id == document_id)
    ).all()

    return DocumentDetail(
        **DocumentSummary.model_validate(document).model_dump(),
        findings=[FindingOut.model_validate(f) for f in findings],
        checks=[CheckRunOut.model_validate(c) for c in checks],
        extracted={r.field_name: r.field_value or "" for r in extracted_rows},
        has_blocking=any(f.severity == "blocking" for f in findings),
        reviewed_at=document.reviewed_at,
        decision_reason=document.decision_reason,
        override_note=document.override_note,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    user: CurrentUserDep,
    session: Annotated[Session, Depends(get_app_session)],
) -> DocumentDetail:
    return _load_detail(session, document_id)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    user: CurrentUserDep,
    session: Annotated[Session, Depends(get_app_session)],
) -> Response:
    """Stream the stored document.

    Addressed by database ID. The filename on disk is read from the row, never
    from the request, so there is no user-supplied path anywhere in this route.
    """
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document_not_found")
    try:
        data = storage.read_stored(document.stored_filename)
    except (storage.UploadRejected, OSError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document_not_found") from None

    return Response(
        content=data,
        media_type=document.mime_type,
        headers={
            # Never let a stored document be interpreted as something else, and
            # never let it run in our origin.
            "Content-Disposition": f'inline; filename="{document.public_ref}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
            "Cache-Control": "private, no-store",
        },
    )
