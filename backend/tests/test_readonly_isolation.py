"""The core claim: the system can read, and cannot write.

Two tests, and they are meant to be read aloud as much as run:

1. Nothing under `app/agents/` can reach the read-write engine. Proved by
   walking the import graph, not by grep — a docstring saying "must not import
   app.db.app" contains that string, and a grep would call it a violation.

2. A check that tries to write is stopped by the database driver, not by the
   application. The read-only connection raises before anything reaches the file.

The second is the one that matters. The first can be satisfied by discipline;
only the second is enforced by something other than our own care.
"""

import ast
from collections import deque
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.readonly import readonly_engine, readonly_session_scope
from app.models.reference import RegistryRecord
from app.providers.records import SeededRecordsProvider

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = "app.db.app"


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _module_path(module: str) -> Path | None:
    if not module.startswith("app"):
        return None
    parts = module.split(".")
    candidate = APP_ROOT.parent.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    package = APP_ROOT.parent.joinpath(*parts) / "__init__.py"
    return package if package.exists() else None


def test_agents_cannot_reach_the_write_engine():
    """Walk every import reachable from app/agents/ and assert app.db.app is not
    among them, reporting the chain if it ever is."""
    seeds = sorted((APP_ROOT / "agents").rglob("*.py"))
    assert seeds, "expected modules under app/agents/"

    seen: set[Path] = set()
    queue: deque[tuple[Path, list[str]]] = deque((p, [p.name]) for p in seeds)
    violations: list[str] = []

    while queue:
        path, chain = queue.popleft()
        if path in seen:
            continue
        seen.add(path)
        for module in sorted(_imports_of(path)):
            if module == FORBIDDEN or module.startswith(FORBIDDEN + "."):
                violations.append(" -> ".join([*chain, module]))
            nxt = _module_path(module)
            if nxt is not None and nxt not in seen:
                queue.append((nxt, [*chain, nxt.name]))

    assert not violations, (
        "app/agents/ can reach the read-write engine:\n  " + "\n  ".join(violations)
    )
    # The walk must actually have gone somewhere, or it proves nothing.
    assert len(seen) > len(seeds), "the import walk did not leave app/agents/"


def test_a_check_cannot_insert():
    """A write through the read-only connection is refused by the driver."""
    with readonly_session_scope() as session:
        with pytest.raises(OperationalError) as raised:
            session.execute(
                text(
                    "INSERT INTO registry_records "
                    "(record_ref, doc_type, full_name, is_sample) "
                    "VALUES ('FORGED-1', 'birth_certificate', 'Somebody', 1)"
                )
            )
            session.commit()

    assert "readonly database" in str(raised.value), str(raised.value)


def test_a_check_cannot_update_or_delete():
    """The same holds for changing or removing an existing record."""
    for statement in (
        "UPDATE registry_records SET full_name = 'Changed'",
        "DELETE FROM registry_records",
        "UPDATE documents SET status = 'approved'",
        "DROP TABLE audit_log",
    ):
        with readonly_session_scope() as session:
            with pytest.raises(OperationalError) as raised:
                session.execute(text(statement))
                session.commit()
            assert "readonly" in str(raised.value).lower(), statement


def test_the_records_provider_can_still_read(seeded_reference):
    """The connection is read-only, not useless — the check's actual job works."""
    with readonly_session_scope() as session:
        record = SeededRecordsProvider(session).find(
            doc_type="birth_certificate", record_ref="BC-4471", full_name=None
        )
    assert record is not None
    assert record.fields["full_name"] == "Rajesh Kumar"
    assert record.is_sample is True, "seeded rows must declare themselves sample data"


def test_the_read_only_url_is_actually_read_only():
    """The engine is configured the way the claim in the README describes."""
    url = str(readonly_engine.url)
    assert "mode=ro" in url, url
    assert "uri=true" in url, url


def test_orm_writes_through_the_read_only_session_are_refused(seeded_reference):
    """Not just raw SQL: the ORM path a check would actually use is refused too."""
    with readonly_session_scope() as session:
        session.add(
            RegistryRecord(
                record_ref="FORGED-2",
                doc_type="birth_certificate",
                full_name="Somebody Else",
                is_sample=True,
            )
        )
        with pytest.raises(OperationalError) as raised:
            session.flush()
        assert "readonly database" in str(raised.value)
