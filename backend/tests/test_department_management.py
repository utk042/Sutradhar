"""A head of department runs their own office, and only their own.

Being a head is authority within an office, not across offices. Every test that
matters here is about the second half of that sentence.
"""

from sqlalchemy import select

from app.db.app import AppSessionLocal
from app.models.decision import Decision
from app.models.department import Department
from app.models.document import Document
from app.models.user import User
from app.services import audit
from app.services.decisions import current_decision, decision_history

PASSWORD = "a-long-enough-password"


def _other_department_officer_id() -> int:
    with AppSessionLocal() as session:
        welfare = session.scalars(select(Department).where(Department.code == "WEL")).first()
        return session.scalars(
            select(User).where(User.department_id == welfare.id, User.role == "officer")
        ).first().id


# --------------------------------------------------------------------------
# Only a head, and only their own office
# --------------------------------------------------------------------------


def test_an_officer_cannot_use_any_of_it(officer):
    for method, path in [
        ("get", "/api/department"),
        ("get", "/api/department/stats"),
        ("get", "/api/department/officers"),
        ("get", "/api/department/audit"),
        ("get", "/api/department/provider"),
    ]:
        assert getattr(officer, method)(path).status_code == 403, path

    assert officer.post(
        "/api/department/officers",
        json={"mobile_number": "9111111111", "full_name": "Somebody", "password": PASSWORD},
    ).status_code == 403


def test_a_head_sees_only_their_own_department(dept_head, other_head):
    mine = dept_head.get("/api/department").json()
    theirs = other_head.get("/api/department").json()
    assert mine["code"] == "REG"
    assert theirs["code"] == "WEL"
    assert mine["id"] != theirs["id"]


def test_the_roster_holds_only_this_department(dept_head):
    roster = dept_head.get("/api/department/officers").json()
    codes = {row["mobile_number"] for row in roster}
    assert "9000000001" in codes          # this office's officer
    assert "9000000011" not in codes      # the other office's officer


# --------------------------------------------------------------------------
# Creating officers
# --------------------------------------------------------------------------


def test_a_head_creates_an_officer_in_their_own_department(dept_head):
    created = dept_head.post(
        "/api/department/officers",
        json={"mobile_number": "9222222222", "full_name": "New Officer", "password": PASSWORD},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "officer"
    assert body["is_active"] is True

    with AppSessionLocal() as session:
        officer = session.get(User, body["id"])
        head = session.scalars(select(User).where(User.mobile_number == "9000000002")).first()
        # The department is not a parameter — it comes from the head.
        assert officer.department_id == head.department_id
        assert officer.created_by == head.id
        # The password is stored hashed, never in the clear.
        assert officer.password_hash != PASSWORD
        assert officer.password_hash.startswith("$argon2")


def test_the_new_officer_can_sign_in(dept_head, client):
    dept_head.post(
        "/api/department/officers",
        json={"mobile_number": "9333333333", "full_name": "Third Officer", "password": PASSWORD},
    )
    signed_in = client.post(
        "/api/auth/login", json={"mobile_number": "9333333333", "password": PASSWORD}
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["role"] == "officer"


def test_a_mobile_number_already_in_use_is_refused(dept_head):
    response = dept_head.post(
        "/api/department/officers",
        json={"mobile_number": "9000000011", "full_name": "Clash", "password": PASSWORD},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "mobile_already_registered"


def test_a_short_password_is_refused(dept_head):
    response = dept_head.post(
        "/api/department/officers",
        json={"mobile_number": "9444444444", "full_name": "Weak", "password": "short"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Suspending officers
# --------------------------------------------------------------------------


def test_suspending_an_officer_takes_effect_at_once(dept_head, officer):
    assert officer.get("/api/auth/me").status_code == 200

    with AppSessionLocal() as session:
        target = session.scalars(
            select(User).where(User.mobile_number == "9000000001")
        ).first().id

    response = dept_head.post(
        f"/api/department/officers/{target}/active", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Their existing session stops working on the very next request.
    assert officer.get("/api/auth/me").status_code == 401


def test_suspending_removes_nothing_they_did(dept_head, officer, reviewed_document):
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "Details do not match."},
    )
    with AppSessionLocal() as session:
        target = session.scalars(
            select(User).where(User.mobile_number == "9000000001")
        ).first().id

    dept_head.post(f"/api/department/officers/{target}/active", json={"is_active": False})

    with AppSessionLocal() as session:
        decision = current_decision(session, reviewed_document)
        assert decision is not None
        assert decision.decided_by == target, "their decision stays attributed to them"
        assert session.get(Document, reviewed_document).status == "rejected"


def test_a_head_cannot_suspend_another_departments_officer(dept_head):
    other = _other_department_officer_id()
    response = dept_head.post(
        f"/api/department/officers/{other}/active", json={"is_active": False}
    )
    assert response.status_code == 404

    with AppSessionLocal() as session:
        assert session.get(User, other).is_active is True


def test_a_head_cannot_suspend_themselves(dept_head):
    with AppSessionLocal() as session:
        head_id = session.scalars(
            select(User).where(User.mobile_number == "9000000002")
        ).first().id
    response = dept_head.post(
        f"/api/department/officers/{head_id}/active", json={"is_active": False}
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# Reassignment
# --------------------------------------------------------------------------


def test_a_head_reassigns_a_pending_document(
    dept_head, officer, second_officer_same_department, reviewed_document
):
    with AppSessionLocal() as session:
        target = session.scalars(
            select(User).where(User.mobile_number == "9000000004")
        ).first().id

    response = dept_head.post(
        f"/api/department/documents/{reviewed_document}/assign",
        json={"assigned_to": target},
    )
    assert response.status_code == 200, response.text

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).assigned_to == target

    # It is now on the other officer's desk, and off the first's.
    assert second_officer_same_department.get(
        f"/api/documents/{reviewed_document}"
    ).status_code == 200
    assert officer.get(f"/api/documents/{reviewed_document}").status_code == 404


def test_a_decided_document_cannot_be_reassigned(
    dept_head, officer, second_officer_same_department, reviewed_document
):
    """Moving a decided file would make somebody look accountable for a
    decision they did not make."""
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "rejected", "reason": "Does not match."},
    )
    with AppSessionLocal() as session:
        target = session.scalars(
            select(User).where(User.mobile_number == "9000000004")
        ).first().id

    response = dept_head.post(
        f"/api/department/documents/{reviewed_document}/assign",
        json={"assigned_to": target},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "document_already_decided"


def test_a_document_cannot_be_reassigned_out_of_its_department(
    dept_head, reviewed_document
):
    other = _other_department_officer_id()
    response = dept_head.post(
        f"/api/department/documents/{reviewed_document}/assign",
        json={"assigned_to": other},
    )
    assert response.status_code == 404

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).assigned_to != other


def test_another_departments_head_cannot_reassign_it(other_head, reviewed_document):
    other = _other_department_officer_id()
    response = other_head.post(
        f"/api/department/documents/{reviewed_document}/assign",
        json={"assigned_to": other},
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# The audit trail
# --------------------------------------------------------------------------


def test_the_audit_view_holds_this_departments_history(dept_head, officer, reviewed_document):
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked in person."},
    )
    page = dept_head.get("/api/department/audit").json()

    actions = [row["action"] for row in page["rows"]]
    assert "document_approved" in actions
    assert "document_uploaded" in actions
    assert page["chain_intact"] is True
    assert page["total"] >= len(page["rows"])


def test_the_audit_view_excludes_another_departments_history(
    other_head, officer, reviewed_document
):
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked."},
    )
    page = other_head.get("/api/department/audit").json()
    assert all(row["document_id"] != reviewed_document for row in page["rows"])


def test_the_audit_view_reports_a_broken_chain(dept_head, reviewed_document):
    from sqlalchemy import text

    from app.db.app import app_engine

    with app_engine.begin() as connection:
        connection.execute(
            text("UPDATE audit_log SET action = 'document_approved' WHERE sequence = 1")
        )

    page = dept_head.get("/api/department/audit").json()
    assert page["chain_intact"] is False, "a tampered log must not report itself intact"


# --------------------------------------------------------------------------
# The three numbers
# --------------------------------------------------------------------------


def test_the_numbers_count_only_this_department(dept_head, other_head, officer, reviewed_document):
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked."},
    )

    mine = dept_head.get("/api/department/stats").json()
    theirs = other_head.get("/api/department/stats").json()

    assert mine["processed_today"] == 1
    assert mine["flags_raised"] >= 1
    assert mine["average_seconds"] is not None
    assert theirs["processed_today"] == 0
    assert theirs["flags_raised"] == 0
    assert theirs["average_seconds"] is None


# --------------------------------------------------------------------------
# Which model reads the documents
# --------------------------------------------------------------------------


def test_the_provider_can_be_switched_and_is_audited(dept_head):
    assert dept_head.post(
        "/api/department/provider", json={"provider": "local"}
    ).json()["provider"] == "local"
    assert dept_head.get("/api/department/provider").json()["provider"] == "local"

    page = dept_head.get("/api/department/audit").json()
    assert "provider_changed" in [row["action"] for row in page["rows"]]


def test_an_unknown_provider_is_refused(dept_head):
    response = dept_head.post("/api/department/provider", json={"provider": "something-else"})
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Superseding a decision
# --------------------------------------------------------------------------


def _decide(officer_client, document_id, decision="approved"):
    payload = {"decision": decision}
    if decision == "rejected":
        payload["reason"] = "The date of birth does not match."
    else:
        payload["override_note"] = "Checked the register in person."
    response = officer_client.post(f"/api/documents/{document_id}/decision", json=payload)
    assert response.status_code == 200, response.text


def test_a_head_supersedes_an_officers_decision(dept_head, officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")

    response = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "The register entry was misread."},
    )
    assert response.status_code == 200, response.text

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "rejected"
        history = decision_history(session, reviewed_document)
        assert len(history) == 2, "the original decision must still be there"

        original, replacement = history
        # The original is untouched apart from the link, and still theirs.
        assert original.decision == "approved"
        assert original.decided_as == "officer"
        assert original.superseded_by == replacement.id
        assert replacement.decision == "rejected"
        assert replacement.decided_as == "dept_head"
        assert replacement.reason == "The register entry was misread."
        assert current_decision(session, reviewed_document).id == replacement.id


def test_superseding_is_audited_with_who_was_overruled(dept_head, officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")
    dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "Misread."},
    )

    page = dept_head.get("/api/department/audit").json()
    row = next(r for r in page["rows"] if r["action"] == "decision_superseded")
    assert row["document_id"] == reviewed_document
    assert "originally_decided_by" in row["detail_json"]
    assert page["chain_intact"] is True


def test_superseding_always_requires_a_reason(dept_head, officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")
    response = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "   "},
    )
    assert response.status_code == 422 or response.json()["detail"] == "reason_required"

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "approved"


def test_an_undecided_document_cannot_be_superseded(dept_head, reviewed_document):
    response = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "Too early."},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "document_not_decided"


def test_superseding_with_the_same_decision_is_refused(dept_head, officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")
    response = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "approved", "reason": "Agreeing loudly."},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "decision_unchanged"


def test_an_officer_cannot_supersede(officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")
    response = officer.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "Changed my mind."},
    )
    assert response.status_code == 403


def test_another_departments_head_cannot_supersede(other_head, officer, reviewed_document):
    _decide(officer, reviewed_document, "approved")
    response = other_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "Not my office."},
    )
    assert response.status_code == 404

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "approved"


def test_superseding_over_a_blocking_finding_still_needs_a_note(
    dept_head, officer, reviewed_document
):
    _decide(officer, reviewed_document, "rejected")
    refused = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "approved", "reason": "I disagree with the rejection."},
    )
    assert refused.status_code == 400
    assert refused.json()["detail"] == "override_note_required"

    allowed = dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={
            "decision": "approved",
            "reason": "I disagree with the rejection.",
            "override_note": "Confirmed against the paper register.",
        },
    )
    assert allowed.status_code == 200


def test_a_decision_row_is_never_deleted(dept_head, officer, reviewed_document):
    """Three decisions in a row leave three rows, not one."""
    _decide(officer, reviewed_document, "approved")
    dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={"decision": "rejected", "reason": "First correction."},
    )
    dept_head.post(
        f"/api/documents/{reviewed_document}/supersede",
        json={
            "decision": "approved",
            "reason": "Second correction.",
            "override_note": "Register confirmed.",
        },
    )

    with AppSessionLocal() as session:
        history = decision_history(session, reviewed_document)
        assert [d.decision for d in history] == ["approved", "rejected", "approved"]
        # Only the last one is in force; the other two point at their successor.
        assert [d.superseded_by is None for d in history] == [False, False, True]
        assert session.scalar(
            select(Decision).where(Decision.document_id == reviewed_document).limit(1)
        ) is not None
