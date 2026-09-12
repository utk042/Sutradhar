"""The retrieval check: which rules apply to this document.

Reads `rules` through the READ-ONLY session and reports what the file will be
judged against. It decides nothing — its value to an officer is transparency:
the rules being applied are named on screen rather than implied by the results.

It runs alongside the other checks rather than before them. Compliance reads the
same rules itself, so nothing waits on this.
"""

import logging
import time

from app.agents.config import CheckConfig
from app.models.types import utcnow
from app.providers.records import RulesProvider
from app.schemas.finding import CheckResult, Finding

logger = logging.getLogger(__name__)


async def run_retrieval(
    *,
    config: CheckConfig,
    doc_type: str,
    extracted: dict[str, str],
    raw_text: str,
    rules: RulesProvider,
    **_: object,
) -> CheckResult:
    started_at = utcnow()
    started = time.perf_counter()

    applicable = rules.for_document_type(doc_type)
    findings: list[Finding] = []

    if not applicable:
        findings.append(
            Finding(
                agent=config.name,
                field="rules",
                status="unverifiable",
                severity="warning",
                document_value=None,
                reference_value=None,
                reference_source="rules",
                explanation_en=(
                    "No rules are recorded for this kind of document, so nothing "
                    "could be checked against them. Please apply your own judgement."
                ),
                confidence=0.5,
            )
        )
    else:
        summary = "; ".join(rule.description_en for rule in applicable)
        findings.append(
            Finding(
                agent=config.name,
                field="rules",
                status="verified",
                severity="info",
                document_value=None,
                reference_value=summary,
                reference_source=", ".join(rule.citation for rule in applicable),
                explanation_en=(
                    f"This document is checked against {len(applicable)} "
                    f"{'rule' if len(applicable) == 1 else 'rules'} for its type. "
                    "Open the evidence to read them."
                ),
                confidence=1.0,
            )
        )

    return CheckResult(
        agent=config.name,
        findings=findings,
        started_at=started_at,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
