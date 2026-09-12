"""Running the checks and persisting what they found.

This module is the boundary. Above it, checks are pure: they read through a
read-only session and return Pydantic findings. Below it, the application layer
opens a write session and stores those findings, the run timings and the audit
row.

That split is why "the system can read, never write" holds for the system's own
bookkeeping too — an agent cannot persist its own conclusions any more than it
can alter a citizen's record.
"""

import logging

from sqlalchemy.orm import Session

from app.agents.graph import run_pipeline
from app.config import get_settings
from contextlib import contextmanager

from app.db.readonly import readonly_session_scope
from app.models.document import Document
from app.models.finding import AgentRun, Finding as FindingRow
from app.models.types import utcnow
from app.providers.base import ProviderUnavailable
from app.providers.records import SeededRecordsProvider, SeededRulesProvider
from app.providers.registry import get_provider
from app.schemas.finding import CheckResult, Finding
from app.services import audit, storage
from app.services.events import ProgressEvent, broker
from app.services.extraction import extract_document

logger = logging.getLogger(__name__)


async def run_checks_for_document(session: Session, document: Document) -> None:
    """Read the document, run the checks, store the results.

    On any failure the document ends in a state the officer can act on — never
    silently stuck. An unreadable document produces an `unverifiable` finding
    saying so, which is the honest outcome.
    """
    document.status = "processing"
    session.commit()
    broker.publish(ProgressEvent(document_id=document.id, kind="reading"))

    audit.record(
        session,
        action="checks_started",
        document_id=document.id,
        detail={"doc_type": document.doc_type},
    )
    session.commit()

    results: list[CheckResult] = []
    extracted: dict[str, str] = {}
    raw_text = ""

    try:
        data = storage.read_stored(document.stored_filename)
        provider = get_provider(session)
        raw_text, extracted, method = await extract_document(
            data=data, mime_type=document.mime_type, provider=provider
        )
        logger.info("document %s read via %s, %d fields", document.id, method, len(extracted))
        document.extracted_text = raw_text

        # The checks' only database access. Each one opens its own read-only
        # session, on its own thread — a session cannot be shared across
        # threads, and a read-only connection has no write lock to contend for.
        @contextmanager
        def open_providers():
            with readonly_session_scope() as read_session:
                yield (
                    SeededRecordsProvider(read_session),
                    SeededRulesProvider(read_session),
                )

        def on_progress(kind: str, label_key: str, data: dict) -> None:
            broker.publish(
                ProgressEvent(
                    document_id=document.id,
                    kind=kind,
                    label_key=label_key or None,
                    data=data,
                )
            )

        classified, results = await run_pipeline(
            document_id=document.id,
            doc_type=document.doc_type,
            extracted=extracted,
            raw_text=raw_text,
            open_providers=open_providers,
            on_progress=on_progress,
            check_delay_ms=get_settings().check_delay_ms,
        )
        # The classification comes back as data and is written here, by the
        # application layer. The graph never holds a writable session.
        document.doc_type = classified

    except ProviderUnavailable as exc:
        logger.warning("document %s could not be read: %s", document.id, exc)
        results = [
            CheckResult(
                agent="verification",
                started_at=utcnow(),
                duration_ms=0,
                findings=[
                    Finding(
                        agent="verification",
                        field="document_content",
                        status="unverifiable",
                        severity="blocking",
                        document_value=None,
                        reference_value=None,
                        reference_source="uploaded document",
                        explanation_en=(
                            "The text of this document could not be read automatically, "
                            "so none of the usual checks could run. Please read the "
                            "document yourself before deciding."
                        ),
                        confidence=0.0,
                    )
                ],
            )
        ]
    except Exception:
        logger.exception("document %s: checks failed", document.id)
        document.status = "failed"
        session.commit()
        broker.publish(
            ProgressEvent(document_id=document.id, kind="complete", data={"status": "failed"})
        )
        audit.record(
            session, action="checks_completed", document_id=document.id,
            detail={"outcome": "failed"},
        )
        session.commit()
        return

    _persist(session, document, results, extracted)


def _persist(
    session: Session,
    document: Document,
    results: list[CheckResult],
    extracted: dict[str, str],
) -> None:
    from app.models.document import ExtractedField

    for field_name, value in extracted.items():
        session.add(
            ExtractedField(
                document_id=document.id,
                field_name=field_name,
                field_value=value,
                confidence=1.0,
            )
        )

    for result in results:
        run = AgentRun(
            document_id=document.id,
            agent_name=result.agent,
            status="failed" if result.failed else "succeeded",
            started_at=result.started_at,
            finished_at=result.finished_at,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
        )
        session.add(run)
        session.flush()  # need run.id for the findings below

        for finding in result.findings:
            session.add(
                FindingRow(
                    document_id=document.id,
                    agent_run_id=run.id,
                    agent=finding.agent,
                    field=finding.field,
                    status=finding.status,
                    severity=finding.severity,
                    document_value=finding.document_value,
                    reference_value=finding.reference_value,
                    reference_source=finding.reference_source,
                    explanation_en=finding.explanation_en,
                    confidence=finding.confidence,
                )
            )

    # The checks are done. The document now waits for a person — this is the
    # review gate, and nothing below this line decides anything.
    document.status = "pending_review"
    session.commit()

    broker.publish(
        ProgressEvent(
            document_id=document.id,
            kind="complete",
            data={
                "status": "pending_review",
                "findings": sum(len(r.findings) for r in results),
                "flagged": sum(
                    1 for r in results for f in r.findings if f.status != "verified"
                ),
            },
        )
    )

    audit.record(
        session,
        action="checks_completed",
        document_id=document.id,
        detail={
            "outcome": "pending_review",
            "checks": len(results),
            "findings": sum(len(r.findings) for r in results),
        },
    )
    session.commit()
