"""The LangGraph orchestration graph.

Shape:

    classify ──> run_specialists ──> assemble  ──> END
                        │
                 asyncio.gather over every enabled check

The specialists node runs every enabled check concurrently, so total wall time is
the slowest check rather than the sum.

`asyncio.gather` alone does not achieve that. It interleaves coroutines only
where they await, and these checks are synchronous work — SQLite reads and
comparisons — that never yields. Gathered directly they run one after another,
which measurement confirmed: three checks starting 0 ms, 2.95 ms and 4.32 ms
apart, with wall time equal to the sum.

So each check is dispatched with `asyncio.to_thread`, and each opens its own
read-only session inside its own thread. SQLAlchemy sessions are not safe to
share across threads, and a read-only connection has no write lock to contend
for, so a session per check is both the correct and the cheapest answer. SQLite
releases the GIL for the duration of a query, so the reads genuinely overlap; a
check that calls a model overlaps for the whole call.

Nothing in this module — or anything it imports — may touch app.db.app. Checks
receive a RecordsProvider backed by the READ-ONLY session and return Pydantic
findings. Persisting them is the application layer's job.
"""

import asyncio
import logging
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.compliance import run_compliance
from app.agents.config import load_pipeline
from app.agents.retrieval import run_retrieval
from app.agents.verification import run_verification
from app.models.types import utcnow
from app.providers.records import RecordsProvider, RulesProvider
from app.schemas.finding import CheckResult

logger = logging.getLogger(__name__)


def _merge(left: list, right: list) -> list:
    return [*left, *right]


#: Opens a read-only session and the providers over it, for the duration of one
#: check. Supplied by the application layer so that nothing under app/agents/
#: needs to import a database module at all.
ProviderScope = Callable[[], AbstractContextManager[tuple[RecordsProvider, RulesProvider]]]

#: Called as each check starts and finishes, so the officer's screen can follow
#: along. Supplied by the application layer: the graph reports progress but knows
#: nothing about how it is delivered.
ProgressHook = Callable[[str, str, dict], None]


def _no_progress(kind: str, label_key: str, data: dict) -> None:
    """Default hook. Running the graph without one is valid and silent."""


class PipelineState(TypedDict, total=False):
    document_id: int
    doc_type: str
    raw_text: str
    extracted: dict[str, str]
    open_providers: ProviderScope
    on_progress: ProgressHook
    #: Demonstration aid; zero in normal operation. Applied inside the gather, so
    #: it slows each check without serialising them.
    check_delay_ms: int
    results: Annotated[list[CheckResult], _merge]


#: Which coroutine implements each configured check. Every runner takes the same
#: keyword arguments and ignores the ones it does not need, so adding a check is
#: an entry here plus a block in pipeline.yaml.
RUNNERS = {
    "verification": run_verification,
    "retrieval": run_retrieval,
    "compliance": run_compliance,
}


def classify(state: PipelineState) -> dict[str, Any]:
    """Decide what kind of document this is from the fields that were read.

    Deliberately simple and inspectable. A model could do this, but the document
    type only selects which checks run — a wrong guess should be cheap and
    visible, not buried in a generation.
    """
    fields = state.get("extracted", {})
    doc_type = state.get("doc_type") or "unknown"
    if doc_type == "unknown":
        if "annual_income" in fields:
            doc_type = "income_certificate"
        elif "date_of_birth" in fields:
            doc_type = "birth_certificate"
    logger.info("document %s classified as %s", state.get("document_id"), doc_type)
    return {"doc_type": doc_type}


async def run_specialists(state: PipelineState) -> dict[str, Any]:
    pipeline = load_pipeline()
    checks = [c for c in pipeline.enabled_checks if c.name in RUNNERS]

    open_providers = state["open_providers"]
    on_progress = state.get("on_progress") or _no_progress

    on_progress("checks_started", "", {"total": len(checks)})

    def run_in_thread(config) -> CheckResult:
        """One check, on its own thread, with its own read-only session."""
        with open_providers() as (records, rules):
            return asyncio.run(
                RUNNERS[config.name](
                    config=config,
                    doc_type=state["doc_type"],
                    extracted=state.get("extracted", {}),
                    raw_text=state.get("raw_text", ""),
                    records=records,
                    rules=rules,
                )
            )

    async def run_one(config) -> CheckResult:
        # Published from the event loop, not the worker thread, so the hook does
        # not need to be thread-safe.
        on_progress("check_started", config.label_key, {"name": config.name})
        try:
            delay_ms = state.get("check_delay_ms") or 0
            if delay_ms:
                await asyncio.sleep(delay_ms / 1000)
            result = await asyncio.to_thread(run_in_thread, config)
            on_progress(
                "check_finished",
                config.label_key,
                {
                    "name": config.name,
                    "duration_ms": result.duration_ms,
                    "findings": len(result.findings),
                },
            )
            return result
        except Exception as exc:  # a failing check must not fail the whole run
            logger.exception("check %s failed", config.name)
            on_progress("check_failed", config.label_key, {"name": config.name})
            return CheckResult(
                agent=config.name,
                findings=[],
                started_at=utcnow(),
                duration_ms=0,
                failed=True,
                error_message=f"{type(exc).__name__}",
            )

    # This is the parallelism.
    results = await asyncio.gather(*(run_one(c) for c in checks))
    return {"results": list(results)}


def assemble(state: PipelineState) -> dict[str, Any]:
    """Collect the findings. The graph stops here — a human decides next."""
    total = sum(len(r.findings) for r in state.get("results", []))
    logger.info(
        "document %s: %d findings from %d checks",
        state.get("document_id"),
        total,
        len(state.get("results", [])),
    )
    return {}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("classify", classify)
    graph.add_node("run_specialists", run_specialists)
    graph.add_node("assemble", assemble)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "run_specialists")
    graph.add_edge("run_specialists", "assemble")
    graph.add_edge("assemble", END)
    return graph.compile()


COMPILED = build_graph()


async def run_pipeline(
    *,
    document_id: int,
    doc_type: str,
    extracted: dict[str, str],
    raw_text: str,
    open_providers: ProviderScope,
    on_progress: ProgressHook | None = None,
    check_delay_ms: int = 0,
) -> tuple[str, list[CheckResult]]:
    """Run the graph. Returns the classified type and every check's result.

    The classification is returned rather than written here — this module has no
    database access of any kind, and that is deliberate.
    """
    final = await COMPILED.ainvoke(
        {
            "document_id": document_id,
            "doc_type": doc_type,
            "extracted": extracted,
            "raw_text": raw_text,
            "open_providers": open_providers,
            "on_progress": on_progress or _no_progress,
            "check_delay_ms": check_delay_ms,
        }
    )
    return final.get("doc_type", doc_type), final.get("results", [])
