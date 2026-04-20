"""IngestionPipeline — the single entry point for all sensor data.

Wires IDataSource → IDetector → IEventBus. Has no knowledge of:
  - Where data comes from (WebSocket or Simulator)
  - How detection works internally
  - Where processed results go (database, broadcast, or both)
"""
from __future__ import annotations

import logging

from interfaces import IDataSource, IDetector, IEventBus

log = logging.getLogger("riglab.pipeline")


class IngestionPipeline:
    """Drives a single source through detection and publishes results.

    Lifecycle: callers `await run(source)` for the duration of a session.
    The coroutine exits when the source is exhausted or raises (e.g.
    WebSocketDisconnect), propagating the exception to the caller.
    """

    def __init__(self, detector: IDetector, bus: IEventBus) -> None:
        self._detector = detector
        self._bus = bus

    async def run(self, source: IDataSource) -> None:
        async for payload in source.stream():
            try:
                state = self._detector.evaluate(payload)
                await self._bus.publish(state)
            except Exception as exc:
                log.error("pipeline error on payload ts=%.3f: %s", payload.timestamp, exc)
