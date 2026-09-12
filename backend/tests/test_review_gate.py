"""The review gate: a decision needs a person, and only one route can make one.

The claim is structural, not procedural — "no other route writes an approval"
has to be true of the code, not of our intentions. So the first test reads the
source: every assignment of a decision value to a document's status must live in
app/api/review.py. The rest exercise the route itself.
"""

import ast
from pathlib import Path

from sqlalchemy import select

from app.db.app import AppSessionLocal
from app.models.audit import AuditLogEntry
from app.models.document import Document
from app.models.finding import Finding as FindingRow

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
DECISIONS = {"approved", "rejected"}
THE_ONLY_GATE = "api/review.py"


def _decision_writes(path: Path) -> list[int]:
    """Line numbers where this module assigns a decision to a document's status."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    lines: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        # `document.status = "approved"` — a literal decision value.
        literal = (
            isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and node.value.value in DECISIONS
        )
        # `document.status = payload.decision` — a value from the request.
        from_payload = isinstance(node.value, ast.Attribute) and node.value.attr == "decision"
        if not (literal or from_payload):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "status":
                lines.append(node.lineno)
    return lines


def test_only_the_review_route_writes_a_decision():
    """Nothing anywhere else in the application moves a document to a decision."""
    offenders: dict[str, list[int]] = {}
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative = path.relative_to(APP_ROOT).as_posix()
        writes = _decision_writes(path)
        if writes and relative != THE_ONLY_GATE:
            offenders[relative] = writes

    assert not offenders, (
        "a decision is written outside the review gate: "
        + ", ".join(f"{where} line(s) {lines}" for where, lines in offenders.items())
    )

    # And the gate itself must actually contain one, or the test above passes
    # simply because nothing writes a decision at all.
    gate_writes = _decision_writes(APP_ROOT / THE_ONLY_GATE)
    assert gate_writes, f"expected {THE_ONLY_GATE} to write a decision"


def test_deciding_requires_a_session(anonymous, reviewed_document):
    response = anonymous.post(
        f"/api/documents/{reviewed_document}/decision", json={"decision": "approved"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "not_authenticated"

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "pending_review"


def test_a_tampered_session_cannot_decide(anonymous, reviewed_document):
    anonymous.cookies.set("sutradhar_access", "not.a.real.token")
    response = anonymous.post(
        f"/api/documents/{reviewed_document}/decision", json={"decision": "approved"}
    )
    assert response.status_code == 401


def test_approving_records_who_and_when(officer, reviewed_document):
    response = officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked the register in person."},
    )
    assert response.status_code == 200, response.text

    with AppSessionLocal() as session:
        document = session.get(Document, reviewed_document)
        assert document.status == "approved"
        assert document.reviewed_by is not None
        assert document.reviewed_at is not None
        assert document.override_note == "Checked the register in person."


def test_a_document_cannot_be_decided_twice(officer, reviewed_document):
    first = officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked."},
    )
    assert first.status_code == 200

    second = officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "Changed my mind."},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "document_not_awaiting_review"

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "approved"


def test_a_document_cannot_be_decided_before_its_checks_finish(officer, sample_pdf):
    """A document still being read is not ready for a person to judge."""
    created = officer.post(
        "/api/documents", files={"file": ("c.pdf", sample_pdf, "application/pdf")}
    ).json()

    with AppSessionLocal() as session:
        document = session.get(Document, created["id"])
        document.status = "processing"
        session.commit()

    response = officer.post(
        f"/api/documents/{created['id']}/decision", json={"decision": "approved"}
    )
    assert response.status_code == 409


def test_rejecting_requires_a_reason(officer, reviewed_document):
    empty = officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "   "},
    )
    assert empty.status_code == 400
    assert empty.json()["detail"] == "reason_required"

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "pending_review"

    given = officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "No matching entry in the records."},
    )
    assert given.status_code == 200
    with AppSessionLocal() as session:
        document = session.get(Document, reviewed_document)
        assert document.status == "rejected"
        assert document.decision_reason == "No matching entry in the records."


def test_approving_over_a_blocking_finding_requires_a_note(officer, reviewed_document):
    with AppSessionLocal() as session:
        blocking = session.scalars(
            select(FindingRow).where(
                FindingRow.document_id == reviewed_document,
                FindingRow.severity == "blocking",
            )
        ).all()
        assert blocking, "this fixture should produce a blocking finding"

    refused = officer.post(
        f"/api/documents/{reviewed_document}/decision", json={"decision": "approved"}
    )
    assert refused.status_code == 400
    assert refused.json()["detail"] == "override_note_required"

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "pending_review"


def test_the_decision_and_its_audit_row_commit_together(officer, reviewed_document):
    with AppSessionLocal() as session:
        before = len(session.scalars(select(AuditLogEntry)).all())

    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "Details do not match."},
    )

    with AppSessionLocal() as session:
        rows = session.scalars(select(AuditLogEntry).order_by(AuditLogEntry.sequence)).all()
        assert len(rows) == before + 1
        last = rows[-1]
        assert last.action == "document_rejected"
        assert last.document_id == reviewed_document
        assert last.actor_user_id is not None


def test_an_unknown_document_is_not_found(officer):
    response = officer.post("/api/documents/99999/decision", json={"decision": "approved"})
    assert response.status_code == 404
    assert response.json()["detail"] == "document_not_found"
