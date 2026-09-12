"""Test fixtures.

Each test module gets its own database file. The settings object is cached and
both engines are built at import time from it, so the environment has to be set
before anything under `app` is imported — which is why this runs at module scope,
before the imports below it.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="sutradhar-tests-"))
os.environ.setdefault("SUTRADHAR_JWT_SECRET", "test-secret-" + "x" * 40)
os.environ["SUTRADHAR_DB_PATH"] = str(_TMP / "test.db")
os.environ["SUTRADHAR_UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["SUTRADHAR_COOKIE_SECURE"] = "false"
os.environ["SUTRADHAR_CHECK_DELAY_MS"] = "0"
os.environ["SUTRADHAR_ENVIRONMENT"] = "development"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from app.config import get_settings  # noqa: E402
from app.db.app import AppSessionLocal, app_engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.reference import RegistryRecord, Rule  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.security import hash_password  # noqa: E402

OFFICER_MOBILE = "9000000001"
DEPT_HEAD_MOBILE = "9000000002"
PASSWORD = "test-password-value"


@pytest.fixture(scope="session", autouse=True)
def database():
    """One schema for the whole session, created directly from the models.

    Alembic is exercised by the clean-clone path in the README; here the point is
    the behaviour of the code above the schema, so create_all is the faster and
    equally faithful route to the same tables.
    """
    settings = get_settings()
    settings.ensure_directories()
    Base.metadata.create_all(app_engine)
    yield
    Base.metadata.drop_all(app_engine)


@pytest.fixture(autouse=True)
def clean_tables(database):
    """Every test starts from the same known state."""
    with AppSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

        session.add_all(
            [
                User(
                    mobile_number=OFFICER_MOBILE,
                    full_name="Test Officer",
                    role="officer",
                    password_hash=hash_password(PASSWORD),
                    is_active=True,
                ),
                User(
                    mobile_number=DEPT_HEAD_MOBILE,
                    full_name="Test Section Head",
                    role="dept_head",
                    password_hash=hash_password(PASSWORD),
                    is_active=True,
                ),
            ]
        )
        session.commit()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def anonymous():
    """A client that has never signed in.

    A separate instance on purpose: `officer` logs in on the shared `client`, so
    a test using both would be authenticated without meaning to be — which is
    exactly the mistake that makes an auth test pass for the wrong reason.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def officer(client):
    """A signed-in officer: the returned client carries the session cookie."""
    response = client.post(
        "/api/auth/login",
        json={"mobile_number": OFFICER_MOBILE, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def dept_head(client):
    response = client.post(
        "/api/auth/login",
        json={"mobile_number": DEPT_HEAD_MOBILE, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def sample_pdf():
    """A birth certificate whose date of birth disagrees with the register."""
    from make_sample_pdf import make_pdf

    return make_pdf(
        [
            "Certificate Number: BC-4471",
            "Name: Rajesh Kumar",
            "Date of Birth: 21/07/1990",
            "Issuing Authority: Municipal Corporation, Jaipur",
        ],
        title="BIRTH CERTIFICATE",
    )


@pytest.fixture
def seeded_reference():
    from datetime import date

    with AppSessionLocal() as session:
        session.add(
            RegistryRecord(
                record_ref="BC-4471",
                doc_type="birth_certificate",
                full_name="Rajesh Kumar",
                date_of_birth=date(1986, 3, 12),
                issuing_authority="Municipal Corporation, Jaipur",
                is_sample=True,
            )
        )
        session.add(
            Rule(
                rule_code="BIRTH_CERT_AUTHORITY",
                doc_type="birth_certificate",
                rule_type="field_format",
                field_name="issuing_authority",
                operator="required",
                severity="warning",
                description_en="A birth certificate must name the authority that issued it.",
                active=True,
            )
        )
        session.commit()


@pytest.fixture
def reviewed_document(officer, sample_pdf, seeded_reference):
    """An uploaded document whose checks have finished, awaiting a decision."""
    response = officer.post(
        "/api/documents",
        files={"file": ("certificate.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    # TestClient runs background tasks before returning, so the checks are done.
    with AppSessionLocal() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.status == "pending_review", document.status
    return document_id
