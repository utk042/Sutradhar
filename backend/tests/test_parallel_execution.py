"""The three checks must run together, not one after another.

This is a structural claim about the graph, so it is tested structurally: the
real runners are replaced with ones that sleep, and the graph is asserted to
finish in about the time of the slowest rather than the sum of all three.

Sleeping runners are the point. The real checks take a millisecond or two
without a model configured, which is too small a signal to distinguish
concurrency from luck; a deliberate delay makes the difference unambiguous.
"""

import asyncio
import time
from contextlib import contextmanager

import pytest

from app.agents import graph as graph_module
from app.agents.config import CheckConfig
from app.models.types import utcnow
from app.schemas.finding import CheckResult

DELAY = 0.20


@contextmanager
def _no_providers():
    """The sleeping runners do not read anything."""
    yield (None, None)


def _sleeping_runner(name: str, seconds: float):
    async def run(*, config: CheckConfig, **_: object) -> CheckResult:
        started_at = utcnow()
        started = time.perf_counter()
        await asyncio.sleep(seconds)
        return CheckResult(
            agent=name,
            findings=[],
            started_at=started_at,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    return run


@pytest.fixture
def sleeping_checks(monkeypatch):
    monkeypatch.setitem(graph_module.RUNNERS, "verification", _sleeping_runner("verification", DELAY))
    monkeypatch.setitem(graph_module.RUNNERS, "retrieval", _sleeping_runner("retrieval", DELAY))
    monkeypatch.setitem(graph_module.RUNNERS, "compliance", _sleeping_runner("compliance", DELAY))


def test_checks_run_concurrently(sleeping_checks):
    started = time.perf_counter()
    _, results = asyncio.run(
        graph_module.run_pipeline(
            document_id=1,
            doc_type="income_certificate",
            extracted={},
            raw_text="",
            open_providers=_no_providers,
        )
    )
    elapsed = time.perf_counter() - started

    assert len(results) == 3, "all three checks should have run"

    sequential = DELAY * len(results)
    # Generous headroom for scheduling, and still far below the sequential time.
    assert elapsed < sequential * 0.6, (
        f"took {elapsed:.3f}s; running one after another would be about "
        f"{sequential:.3f}s, so these did not run together"
    )


def test_check_windows_overlap(sleeping_checks):
    """Each check's recorded window must overlap the others'.

    The timings are what the interface shows an officer under "technical
    details", so they have to reflect what actually happened.
    """
    _, results = asyncio.run(
        graph_module.run_pipeline(
            document_id=1,
            doc_type="income_certificate",
            extracted={},
            raw_text="",
            open_providers=_no_providers,
        )
    )
    starts = [r.started_at for r in results]
    spread = (max(starts) - min(starts)).total_seconds()
    assert spread < DELAY / 2, (
        f"checks began {spread:.3f}s apart, which is too far apart to be concurrent"
    )

    for a in results:
        for b in results:
            if a.agent == b.agent:
                continue
            assert a.started_at < b.finished_at and b.started_at < a.finished_at, (
                f"{a.agent} and {b.agent} did not overlap in time"
            )
