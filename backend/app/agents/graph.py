"""The LangGraph orchestration graph.

Shape:

    classify ──> run_specialists ──> assemble  ──> END
                        │
                 asyncio.gather over every enabled check

The specialists node gathers all enabled checks concurrently, so total wall time
is the slowest check rather than the sum. Phase 2 enables one of them, which is
why the numbers below look like a single duration; the structure is already the
parallel one, so Phase 3 enables two more in pipeline.yaml and nothing here
changes.

Nothing in this module — or anything it imports — may touch app.db.app. Checks
receive a RecordsProvider backed by the READ-ONLY session and return Pydantic
findings. Persisting them is the application layer's job.
"""

import asyncio
import logging
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.config import load_pipeline
from app.models.types import utcnow
from app.agents.verification import run_verification
from app.providers.records import RecordsProvider
from app.schemas.finding import CheckResult

logger = logging.getLogger(__name__)


def _merge(left: list, right: list) -> list:
    return [*left, *right]


class PipelineState(TypedDict, total=False):
    document_id: int
    doc_type: str
    raw_text: str
    extracted: dict[str, str]
    records: RecordsProvider
    results: Annotated[list[CheckResult], _merge]


#: Which coroutine implements each configured check. Phase 3 adds two entries.
RUNNERS = {"verification": run_verification}


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

    async def run_one(config) -> CheckResult:
        try:
            return await RUNNERS[config.name](
                config=config,
                doc_type=state["doc_type"],
                extracted=state.get("extracted", {}),
                raw_text=state.get("raw_text", ""),
                records=state["records"],
            )
        except Exception as exc:  # a failing check must not fail the whole run
            logger.exception("check %s failed", config.name)
            return CheckResult(
                agent=config.name,
                findings=[],
                started_at=utcnow(),
                duration_ms=0,
                failed=True,
                error_message=f"{type(exc).__name__}",
            )

    # This is the parallelism. With one check enabled it is a gather of one.
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
    records: RecordsProvider,
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
            "records": records,
        }
    )
    return final.get("doc_type", doc_type), final.get("results", [])
