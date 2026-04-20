"""InMemoryEventBus — parallel fanout between the pipeline and its subscribers.

All registered handlers receive every ProcessedState in parallel via
asyncio.gather. A slow or failing handler never delays another — each
exception is caught and logged independently so the pipeline continues.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from core.interfaces import IEventBus
from core.schemas import ProcessedState

log = logging.getLogger("riglab.bus")


class InMemoryEventBus(IEventBus):
    """Thread-safe (within a single event loop) publish/subscribe bus.

    Subscribers are registered once at startup via subscribe() and are
    never removed. publish() fires all handlers concurrently.
    """

    def __init__(self) -> None:
        self._handlers: list[Callable[[ProcessedState], Awaitable[None]]] = []

    def subscribe(self, handler: Callable[[ProcessedState], Awaitable[None]]) -> None:
        self._handlers.append(handler)

    async def publish(self, state: ProcessedState) -> None:
        if not self._handlers:
            return
        results = await asyncio.gather(
            *[h(state) for h in self._handlers],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                log.error("event handler failed: %s", result)
