"""The compliance check: thresholds, expiry and required details.

Reads `rules` through the READ-ONLY session and evaluates each one against the
values read off the document. Like every other check it returns findings and
writes nothing.

Each rule type is evaluated by a small, readable function. A rule whose value is
missing or unparseable produces `unverifiable` rather than a pass or a fail —
the system saying it could not tell, which is the honest answer and leaves the
judgement where it belongs.
"""

import logging
import re
import time
from datetime import date

from app.agents.comparison import parse_date
from app.agents.config import CheckConfig, load_pipeline
from app.models.types import utcnow
from app.providers.records import ApplicableRule, RulesProvider
from app.schemas.finding import CheckResult, Finding

logger = logging.getLogger(__name__)

FIELD_NAMES = {
    "annual_income": "annual income",
    "issued_on": "date of issue",
    "issuing_authority": "issuing authority",
    "date_of_birth": "date of birth",
    "full_name": "name",
}


def _describe(field: str | None) -> str:
    if not field:
        return "this document"
    return FIELD_NAMES.get(field, field.replace("_", " "))


def _to_number(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def _format_amount(value: int) -> str:
    """Indian digit grouping: 1,80,000 rather than 180,000."""
    text = str(value)
    if len(text) <= 3:
        return text
    head, tail = text[:-3], text[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def _eligibility(rule: ApplicableRule, value: str | None) -> tuple[str, str, float]:
    if value is None:
        return ("unverifiable",
                f"The {_describe(rule.field_name)} is not stated on the document, so this "
                f"rule could not be checked. {rule.description_en}", 0.3)
    actual, threshold = _to_number(value), _to_number(rule.threshold_value or "")
    if actual is None or threshold is None:
        return ("unverifiable",
                f"The {_describe(rule.field_name)} could not be read as a number, so this "
                f"rule could not be checked. {rule.description_en}", 0.3)

    ops = {
        "<=": actual <= threshold, "<": actual < threshold,
        ">=": actual >= threshold, ">": actual > threshold,
        "==": actual == threshold,
    }
    if rule.operator not in ops:
        return ("unverifiable", f"This rule could not be applied. {rule.description_en}", 0.2)

    if ops[rule.operator]:
        return ("verified",
                f"The {_describe(rule.field_name)} of Rs {_format_amount(actual)} meets the "
                f"requirement. {rule.description_en}", 0.99)
    return ("mismatch",
            f"The {_describe(rule.field_name)} of Rs {_format_amount(actual)} does not meet "
            f"the requirement. {rule.description_en}", 0.98)


def _expiry(rule: ApplicableRule, value: str | None, today: date) -> tuple[str, str, float]:
    if value is None:
        return ("unverifiable",
                f"The {_describe(rule.field_name)} is not stated on the document, so its "
                f"validity could not be checked. {rule.description_en}", 0.3)
    issued = parse_date(value)
    if issued is None:
        return ("unverifiable",
                f"The {_describe(rule.field_name)} could not be read as a date, so its "
                f"validity could not be checked. {rule.description_en}", 0.3)

    months = int(rule.threshold_value or 0)
    age_months = (today.year - issued.year) * 12 + (today.month - issued.month)
    if today.day < issued.day:
        age_months -= 1

    if age_months <= months:
        return ("verified",
                f"The document was issued {age_months} "
                f"{'month' if age_months == 1 else 'months'} ago and is still valid. "
                f"{rule.description_en}", 0.99)
    return ("mismatch",
            f"The document was issued {age_months} months ago and is no longer within its "
            f"validity period. {rule.description_en}", 0.98)


def _required(rule: ApplicableRule, value: str | None) -> tuple[str, str, float]:
    if value and value.strip():
        return ("verified",
                f"The {_describe(rule.field_name)} is present on the document. "
                f"{rule.description_en}", 0.99)
    return ("mismatch",
            f"The {_describe(rule.field_name)} is missing from the document. "
            f"{rule.description_en}", 0.95)


async def run_compliance(
    *,
    config: CheckConfig,
    doc_type: str,
    extracted: dict[str, str],
    raw_text: str,
    rules: RulesProvider,
    today: date | None = None,
    **_: object,
) -> CheckResult:
    started_at = utcnow()
    started = time.perf_counter()
    pipeline = load_pipeline()
    today = today or utcnow().date()

    findings: list[Finding] = []
    for rule in rules.for_document_type(doc_type):
        value = extracted.get(rule.field_name) if rule.field_name else None

        if rule.rule_type == "eligibility":
            status, explanation, confidence = _eligibility(rule, value)
        elif rule.rule_type == "expiry":
            status, explanation, confidence = _expiry(rule, value, today)
        elif rule.rule_type in {"field_format", "required_attachment"}:
            status, explanation, confidence = _required(rule, value)
        else:
            status, explanation, confidence = (
                "unverifiable", f"This rule could not be applied. {rule.description_en}", 0.2)

        # A failed rule carries the severity the rule itself declares; anything
        # the check could not resolve defaults to the configured severity.
        if status == "mismatch":
            severity = rule.severity
        elif status == "unverifiable":
            severity = pipeline.severity_for("default_unverifiable", "warning")
        else:
            severity = "info"

        findings.append(
            Finding(
                agent=config.name,
                field=rule.field_name or "document_content",
                status=status,
                severity=severity,
                document_value=value,
                reference_value=rule.threshold_value,
                reference_source=rule.citation,
                explanation_en=explanation,
                confidence=confidence,
            )
        )

    return CheckResult(
        agent=config.name,
        findings=findings,
        started_at=started_at,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
