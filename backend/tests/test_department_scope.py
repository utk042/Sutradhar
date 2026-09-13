"""One office cannot see another's files.

The boundary is enforced in every query rather than checked once at the door, so
these tests come in two kinds: behavioural ones that try to cross it, and a
structural one asserting that no route reaches a document without going through
`app/api/scope.py` — because the way this breaks in future is somebody adding a
route and forgetting.

A document belonging to another department answers 404 rather than 403. A 403
would confirm it exists, which tells one office something about another's
caseload.
"""

import ast
from pathlib import Path

from sqlalchemy import select

from app.db.app import AppSessionLocal
from app.models.document import Document
from app.models.user import User

API_ROOT = Path(__file__).resolve().parents[1] / "app" / "api"
SCOPE_FUNCTIONS = {"load_visible_document", "visible_documents"}
#: Routes that legitimately never touch a document.
EXEMPT = {"auth.py", "health.py", "deps.py", "scope.py", "__init__.py"}


def test_every_route_module_reaching_a_document_uses_the_scope():
    """A module that queries Document must go through scope.py to do it."""
    offenders: list[str] = []

    for path in sorted(API_ROOT.glob("*.py")):
        if path.name in EXEMPT:
            continue
        source = path.read_text(encoding="utf-8")
        if "Document" not in source:
            continue

        tree = ast.parse(source, str(path))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        if not (called & SCOPE_FUNCTIONS):
            offenders.append(path.name)

    assert not offenders, (
        "these route modules reach a document without the department scope: "
        + ", ".join(offenders)
    )


def test_no_route_loads_a_document_by_primary_key():
    """`session.get(Document, id)` skips every `where` clause, including the
    department one. The scoped loader exists so nothing needs to."""
    offenders: list[str] = []
    for path in sorted(API_ROOT.glob("*.py")):
        if path.name in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "Document"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        "a document is loaded by primary key, bypassing the scope: " + ", ".join(offenders)
    )


# --------------------------------------------------------------------------
# Behaviour
# --------------------------------------------------------------------------


def test_another_department_cannot_see_the_document(other_officer, reviewed_document):
    assert other_officer.get(f"/api/documents/{reviewed_document}").status_code == 404


def test_another_departments_head_cannot_see_it_either(other_head, reviewed_document):
    """Being a head of department is authority within an office, not across."""
    assert other_head.get(f"/api/documents/{reviewed_document}").status_code == 404


def test_another_department_cannot_read_the_file(other_officer, reviewed_document):
    assert other_officer.get(f"/api/documents/{reviewed_document}/file").status_code == 404


def test_another_department_cannot_watch_the_checks(other_officer, reviewed_document):
    assert other_officer.get(f"/api/documents/{reviewed_document}/events").status_code == 404


def test_another_department_cannot_decide_it(other_head, reviewed_document):
    response = other_head.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Not mine to approve."},
    )
    assert response.status_code == 404

    with AppSessionLocal() as session:
        assert session.get(Document, reviewed_document).status == "pending_review"


def test_another_department_does_not_see_it_in_the_list(other_officer, reviewed_document):
    listed = other_officer.get("/api/documents").json()
    assert all(row["id"] != reviewed_document for row in listed)


def test_an_officer_does_not_see_a_colleagues_desk(
    second_officer_same_department, reviewed_document
):
    """Same department, different officer: the file is not on their desk."""
    listed = second_officer_same_department.get("/api/documents").json()
    assert all(row["id"] != reviewed_document for row in listed)
    assert (
        second_officer_same_department.get(f"/api/documents/{reviewed_document}").status_code
        == 404
    )


def test_their_own_head_does_see_it(dept_head, reviewed_document):
    """The boundary is the department, not the desk: the head sees the office."""
    assert dept_head.get(f"/api/documents/{reviewed_document}").status_code == 200
    listed = dept_head.get("/api/documents").json()
    assert any(row["id"] == reviewed_document for row in listed)


def test_an_uploaded_document_takes_its_uploader_s_department(officer, sample_pdf):
    created = officer.post(
        "/api/documents", files={"file": ("c.pdf", sample_pdf, "application/pdf")}
    ).json()

    with AppSessionLocal() as session:
        document = session.get(Document, created["id"])
        uploader = session.get(User, document.uploaded_by)
        assert document.department_id == uploader.department_id
        # And it starts on the uploader's own desk.
        assert document.assigned_to == uploader.id


def test_an_officers_own_screen_counts_only_their_own_desk(
    officer, second_officer_same_department, reviewed_document
):
    """The numbers are per desk, not per office.

    Same department, so the department boundary is not what is being tested
    here: the file is on one officer's desk and must not appear in the other
    officer's counts. `/api/work` is narrowed by `visible_documents`, which for
    an officer already means "assigned to me".
    """
    mine = officer.get("/api/work").json()
    theirs = second_officer_same_department.get("/api/work").json()

    assert mine["pending_now"] == 1
    assert theirs["pending_now"] == 0
    assert theirs["recent"] == []


def test_another_department_is_absent_from_the_officer_screen(
    other_officer, reviewed_document
):
    summary = other_officer.get("/api/work").json()
    assert summary["pending_now"] == 0
    assert summary["flags_waiting"] == 0
    assert summary["recent"] == []


def test_a_decided_file_shows_on_the_deciders_own_screen(officer, reviewed_document):
    officer.post(
        f"/api/documents/{reviewed_document}/decision",
        json={"decision": "approved", "override_note": "Checked against the register."},
    )
    summary = officer.get("/api/work").json()

    assert summary["decided_today"] == 1
    assert summary["decided_total"] == 1
    assert summary["pending_now"] == 0
    assert [row["id"] for row in summary["recent"]] == [reviewed_document]
    assert summary["recent"][0]["status"] == "approved"


def test_the_officer_screen_needs_a_session(anonymous):
    assert anonymous.get("/api/work").status_code == 401
