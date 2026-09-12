"""The audit log: append-only, and tamper-evident.

Each row hashes the one before it, so altering or removing any historical row
breaks the chain from that point on. These tests do the altering, because a
chain that is never attacked proves nothing.

They also assert the log refuses personal data outright. The log is exportable,
and an export must not become a leak.
"""

import json

import pytest
from sqlalchemy import select, text

from app.db.app import AppSessionLocal, app_engine
from app.models.audit import AuditLogEntry
from app.services import audit


def _record_a_few(session):
    """Three rows against real users and documents.

    The audit table carries foreign keys to both, so inventing ids would fail on
    the constraint rather than on anything the tests are about.
    """
    from app.models.document import Document
    from app.models.user import User

    officer_id = session.scalars(select(User).where(User.role == "officer")).first().id

    document_ids = []
    for index in range(1, 4):
        document = Document(
            public_ref=f"DOC-TEST{index}",
            doc_type="birth_certificate",
            original_filename=f"certificate-{index}.pdf",
            stored_filename=f"{index:032x}.pdf",
            mime_type="application/pdf",
            size_bytes=800 + index,
            sha256="0" * 64,
            status="pending_review",
            uploaded_by=officer_id,
        )
        session.add(document)
        session.flush()
        document_ids.append(document.id)
    session.commit()

    for document_id in document_ids:
        audit.record(
            session,
            action="document_uploaded",
            actor_user_id=officer_id,
            actor_role="officer",
            document_id=document_id,
            detail={"mime_type": "application/pdf", "size_bytes": 800},
        )
    session.commit()
    return officer_id, document_ids


def test_a_fresh_chain_is_intact():
    with AppSessionLocal() as session:
        _record_a_few(session)
        intact, broken = audit.verify_chain(session)
    assert intact is True
    assert broken is None


def test_the_first_row_links_to_the_genesis_hash():
    with AppSessionLocal() as session:
        _record_a_few(session)
        first = session.scalars(
            select(AuditLogEntry).order_by(AuditLogEntry.sequence)
        ).first()
    assert first.prev_hash == audit.GENESIS_HASH
    assert first.sequence == 1


def test_each_row_links_to_the_one_before_it():
    with AppSessionLocal() as session:
        _record_a_few(session)
        rows = session.scalars(
            select(AuditLogEntry).order_by(AuditLogEntry.sequence)
        ).all()
    assert len(rows) == 3
    for previous, current in zip(rows, rows[1:]):
        assert current.prev_hash == previous.row_hash
        assert current.sequence == previous.sequence + 1


@pytest.mark.parametrize(
    "describe, build_statement, expected_break",
    [
        (
            "a decision is edited in place",
            lambda officer, other, docs: (
                "UPDATE audit_log SET detail_json = '{\"decision\":\"approved\"}' "
                "WHERE sequence = 3"
            ),
            3,
        ),
        (
            "the action is changed",
            lambda officer, other, docs: (
                "UPDATE audit_log SET action = 'document_approved' WHERE sequence = 2"
            ),
            2,
        ),
        (
            # Re-attributing the act to a real colleague, which is the version of
            # this attack that would otherwise survive a foreign key.
            "it is blamed on somebody else",
            lambda officer, other, docs: (
                f"UPDATE audit_log SET actor_user_id = {other} WHERE sequence = 2"
            ),
            2,
        ),
        (
            "it is re-pointed at a different document",
            lambda officer, other, docs: (
                f"UPDATE audit_log SET document_id = {docs[0]} WHERE sequence = 3"
            ),
            3,
        ),
        (
            "a row is removed from the middle",
            lambda officer, other, docs: "DELETE FROM audit_log WHERE sequence = 2",
            3,
        ),
    ],
)
def test_tampering_is_detected(describe, build_statement, expected_break):
    from app.models.user import User

    with AppSessionLocal() as session:
        officer_id, document_ids = _record_a_few(session)
        other_id = session.scalars(
            select(User).where(User.role == "dept_head")
        ).first().id

    # Straight past the application, the way someone with database access would.
    with app_engine.begin() as connection:
        connection.execute(text(build_statement(officer_id, other_id, document_ids)))

    with AppSessionLocal() as session:
        intact, broken = audit.verify_chain(session)

    assert intact is False, f"tampering went undetected when {describe}"
    assert broken == expected_break, describe


def test_a_forged_row_cannot_be_appended_without_breaking_the_chain():
    """Adding a row by hand fails, because its prev_hash cannot be guessed."""
    with AppSessionLocal() as session:
        _record_a_few(session)

    with app_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_log "
                "(sequence, actor_user_id, actor_role, action, document_id, detail_json,"
                " created_at, prev_hash, row_hash) "
                "VALUES (4, NULL, 'officer', 'document_approved', NULL, '{}',"
                " '2026-01-01 00:00:00', :prev, :row)"
            ),
            {"prev": "0" * 64, "row": "f" * 64},
        )

    with AppSessionLocal() as session:
        intact, broken = audit.verify_chain(session)
    assert intact is False
    assert broken == 4


def test_the_log_refuses_personal_data():
    """Names, dates of birth and document numbers must never be written here."""
    with AppSessionLocal() as session:
        for forbidden in (
            {"full_name": "Rajesh Kumar"},
            {"date_of_birth": "1986-03-12"},
            {"record_ref": "BC-4471"},
            {"mobile_number": "9000000001"},
            {"document_value": "21/07/1990"},
        ):
            with pytest.raises(ValueError, match="personal data"):
                audit.record(session, action="document_uploaded", detail=forbidden)


def test_ordinary_details_are_still_allowed():
    with AppSessionLocal() as session:
        officer_id, document_ids = _record_a_few(session)
        entry = audit.record(
            session,
            action="document_approved",
            actor_user_id=officer_id,
            document_id=document_ids[0],
            detail={"decision": "approved", "over_blocking": True, "reason_given": False},
        )
        session.commit()
        assert json.loads(entry.detail_json)["decision"] == "approved"


def test_the_whole_journey_is_logged(officer, reviewed_document):
    """Upload, checks and decision each leave a row, in order."""
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "Date of birth does not match."},
    )

    with AppSessionLocal() as session:
        actions = [
            row.action
            for row in session.scalars(
                select(AuditLogEntry).order_by(AuditLogEntry.sequence)
            ).all()
        ]
        intact, _ = audit.verify_chain(session)

    assert actions == [
        "document_uploaded",
        "checks_started",
        "checks_completed",
        "document_rejected",
    ]
    assert intact is True


def test_there_is_no_route_that_edits_the_log():
    """No update or delete path for the audit log exists anywhere in the API."""
    from pathlib import Path

    api = Path(__file__).resolve().parents[1] / "app" / "api"
    offenders = []
    for path in sorted(api.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "AuditLogEntry" in source and (".delete(" in source or "update(" in source):
            offenders.append(path.name)
    assert not offenders, f"the audit log is edited in: {offenders}"
