"""Live progress over Server-Sent Events.

One-directional, which is all this needs, and it survives the proxies a
government network puts in the way — which WebSockets frequently do not.

Each event carries a `label_key`, not a sentence. The screen renders the wording
from its own locale file, so nothing user-facing is decided here and switching to
Hindi needs no change on this side.

The stream closes itself once the document reaches a state that waits for a
person. A heartbeat keeps intermediaries from closing an idle connection, and the
screen re-fetches the document on close, so a dropped stream costs a moment, not
correctness.
"""

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep
from app.db.app import get_app_session
from app.models.document import Document
from app.services.events import broker

router = APIRouter(prefix="/documents", tags=["stream"])
logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15
#: A stream is not a place to wait indefinitely; the checks take seconds.
MAX_STREAM_SECONDS = 300

SETTLED = {"pending_review", "approved", "rejected", "failed"}


def _format(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


@router.get("/{document_id}/events")
async def stream_events(
    document_id: int,
    request: Request,
    user: CurrentUserDep,
    session: Annotated[Session, Depends(get_app_session)],
) -> StreamingResponse:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document_not_found")

    initial_status = document.status
    already_settled = initial_status in SETTLED

    async def generate():
        # Subscribing first means anything that happened between the upload
        # response and this connection is replayed rather than missed.
        queue = broker.subscribe(document_id)
        try:
            yield _format("status", {"status": initial_status})

            # Drain the replay before deciding whether there is anything left to
            # wait for. A run that finished moments ago still has its progress to
            # show, and the screen should see the checks, not just the outcome.
            saw_complete = False
            while not queue.empty():
                event = queue.get_nowait()
                payload = {"kind": event.kind, **event.data}
                if event.label_key:
                    payload["label_key"] = event.label_key
                yield _format(event.kind, payload)
                if event.kind == "complete":
                    saw_complete = True

            if saw_complete:
                return
            if already_settled:
                # Settled before this process started tracking it, so there is no
                # progress to replay and nothing further will arrive.
                yield _format("complete", {"status": initial_status})
                return

            elapsed = 0.0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    elapsed += HEARTBEAT_SECONDS
                    if elapsed >= MAX_STREAM_SECONDS:
                        break
                    # A comment line: keeps the connection alive without the
                    # screen having to interpret anything.
                    yield ": keep-alive\n\n"
                    continue

                payload = {"kind": event.kind, **event.data}
                if event.label_key:
                    payload["label_key"] = event.label_key
                yield _format(event.kind, payload)

                if event.kind == "complete":
                    break
        finally:
            broker.unsubscribe(document_id, queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # nginx and several government proxies buffer by default, which
            # defeats streaming entirely.
            "X-Accel-Buffering": "no",
        },
    )
