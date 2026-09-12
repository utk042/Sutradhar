"""The verification check: document fields against the official record.

Reads `registry_records` through the READ-ONLY session and returns Findings. It
holds no write session, opens no transaction, and persists nothing — the caller
does that.
"""

import logging
import time

from app.agents.comparison import compare
from app.agents.config import CheckConfig, load_pipeline
from app.agents.guard import detect_injection
from app.models.types import utcnow
from app.providers.records import RecordsProvider
from app.schemas.finding import CheckResult, Finding

logger = logging.getLogger(__name__)

#: Rendered into explanations. Deliberately the officer's vocabulary, not the
#: database's: never "full_name", always "the name".
FIELD_NAMES = {
    "full_name": "name",
    "date_of_birth": "date of birth",
    "father_name": "father's name",
    "address": "address",
    "annual_income": "annual income",
    "issued_on": "date of issue",
    "issuing_authority": "issuing authority",
}


def _describe(field: str) -> str:
    return FIELD_NAMES.get(field, field.replace("_", " "))


def _explain(field: str, verdict: str, document_value: str, reference_value: str) -> str:
    name = _describe(field)
    if verdict == "verified":
        return f"The {name} on the document matches the official record."
    if verdict == "mismatch":
        return (
            f"The {name} on the document does not match the official record. "
            f"The document says “{document_value}”; the record says “{reference_value}”."
        )
    return (
        f"The {name} could not be confirmed either way. The document says "
        f"“{document_value}”; the record says “{reference_value}”. These may be the "
        f"same, written differently. Please check this one yourself."
    )


async def run_verification(
    *,
    config: CheckConfig,
    doc_type: str,
    extracted: dict[str, str],
    raw_text: str,
    records: RecordsProvider,
) -> CheckResult:
    started_at = utcnow()
    started = time.perf_counter()
    findings: list[Finding] = []
    pipeline = load_pipeline()

    # 1. Anything instruction-shaped in the document is reported, never obeyed.
    for excerpt in detect_injection(raw_text):
        findings.append(
            Finding(
                agent=config.name,
                field="document_content",
                status="unverifiable",
                severity=pipeline.severity_for("injection_detected", "blocking"),
                document_value=excerpt[:200],
                reference_value=None,
                reference_source="uploaded document",
                explanation_en=(
                    "This document contains text that reads like an instruction to the "
                    "system rather than part of a certificate. It has been ignored and "
                    "flagged for you. Please examine the document closely."
                ),
                confidence=0.9,
            )
        )

    # 2. Locate the official record this document claims to correspond to.
    record = records.find(
        doc_type=doc_type,
        record_ref=extracted.get("record_ref"),
        full_name=extracted.get("full_name"),
    )

    if record is None:
        findings.append(
            Finding(
                agent=config.name,
                field="record",
                status="unverifiable",
                severity=pipeline.severity_for("default_unverifiable", "warning"),
                document_value=extracted.get("record_ref") or extracted.get("full_name"),
                reference_value=None,
                reference_source="registry_records",
                explanation_en=(
                    "No matching entry was found in the records for this document. "
                    "The certificate number or name may be different in the records, "
                    "or the entry may not exist. Please check before deciding."
                ),
                confidence=0.6,
            )
        )
        return CheckResult(
            agent=config.name,
            findings=findings,
            started_at=started_at,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # 3. Compare every field present on both sides.
    for field, document_value in extracted.items():
        if field == "record_ref":
            continue
        reference_value = record.fields.get(field)
        if reference_value is None:
            findings.append(
                Finding(
                    agent=config.name,
                    field=field,
                    status="unverifiable",
                    severity=pipeline.severity_for("default_unverifiable", "warning"),
                    document_value=document_value,
                    reference_value=None,
                    reference_source=record.citation,
                    explanation_en=(
                        f"The document gives a {_describe(field)}, but the official "
                        f"record does not hold that detail, so it could not be checked."
                    ),
                    confidence=0.5,
                )
            )
            continue

        verdict, confidence = compare(field, document_value, reference_value)
        severity = "info"
        if verdict == "mismatch":
            severity = pipeline.severity_for(f"{field}_mismatch", "warning")
        elif verdict == "unverifiable":
            severity = pipeline.severity_for(f"{field}_unverifiable", "warning")

        findings.append(
            Finding(
                agent=config.name,
                field=field,
                status=verdict,
                severity=severity,
                document_value=document_value,
                reference_value=reference_value,
                reference_source=record.citation,
                explanation_en=_explain(field, verdict, document_value, reference_value),
                confidence=confidence,
            )
        )

    return CheckResult(
        agent=config.name,
        findings=findings,
        started_at=started_at,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
