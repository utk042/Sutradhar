"""In-process progress events, for the live view of a document's checks.

A tiny publish/subscribe broker keyed by document. The review route subscribes,
the check run publishes, and the API turns each event into a Server-Sent Event.

Deliberately in-process: there is one application process, progress is ephemeral,
and a message broker for this would be infrastructure nobody needs. Running more
than one worker would need a shared broker, and `subscriber_count` exists so that
is measurable rather than a surprise. The screen also falls back to fetching the
document, so a missed event delays the update, it does not lose it.

Each document keeps a short replay buffer. Without one there is a race the
interface cannot win: the screen connects after the upload response returns, and
the checks can finish in the few milliseconds in between, so a subscriber would
see only the final event and never the progress it exists to show. A new
subscriber is handed what has already happened, then follows along live.

Events carry a `label_key`, never a sentence — the officer's screen renders the
wording from its own locale file, so nothing user-facing is decided here and
Hindi needs no change to this module.
"""

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

#: Bounded so a subscriber that stops reading cannot grow without limit. When it
#: fills, the oldest event is dropped: progress is a view of current state, and a
#: stale frame is worth less than the newest one.
QUEUE_SIZE = 64

#: How much history a late subscriber is handed. A run emits two events per
#: check plus a start and a finish, so this holds several runs' worth.
REPLAY_SIZE = 64

#: Documents whose runs have finished are forgotten, so the buffers cannot grow
#: without bound across a long-running process.
MAX_TRACKED_DOCUMENTS = 256


@dataclass(frozen=True)
class ProgressEvent:
    document_id: int
    kind: str
    label_key: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)
        self._history: dict[int, deque[ProgressEvent]] = {}

    def subscribe(self, document_id: int) -> asyncio.Queue:
        """Subscribe, pre-loaded with whatever has already happened."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        for past in self._history.get(document_id, ()):
            try:
                queue.put_nowait(past)
            except asyncio.QueueFull:
                break
        self._subscribers[document_id].add(queue)
        return queue

    def history(self, document_id: int) -> tuple[ProgressEvent, ...]:
        return tuple(self._history.get(document_id, ()))

    def forget(self, document_id: int) -> None:
        self._history.pop(document_id, None)

    def unsubscribe(self, document_id: int, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(document_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(document_id, None)

    def subscriber_count(self, document_id: int) -> int:
        return len(self._subscribers.get(document_id, ()))

    def publish(self, event: ProgressEvent) -> None:
        """Record, then deliver to every subscriber. Safe with no listeners."""
        history = self._history.get(event.document_id)
        if history is None:
            if len(self._history) >= MAX_TRACKED_DOCUMENTS:
                # Drop the oldest document's history rather than grow for ever.
                self._history.pop(next(iter(self._history)), None)
            history = self._history[event.document_id] = deque(maxlen=REPLAY_SIZE)
        history.append(event)

        for queue in tuple(self._subscribers.get(event.document_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()      # drop the oldest
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    logger.debug("dropped a progress event for document %s", event.document_id)


broker = EventBroker()
