"""Boundary contracts between architectural layers.

Three interfaces, three boundaries:
  IDataSource  — ingestion layer (WebSocket or Simulator)
  IDetector    — processing layer (validation + engineering + detection)
  IEventBus    — distribution layer (DB writer + WS broadcaster)

Nothing outside schemas.py crosses these boundaries.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable

from core.schemas import ProcessedState, SensorPayload


class IDataSource(ABC):
    """Produces an async stream of sensor payloads.

    Implementations must know nothing about detection, persistence, or
    how the payloads will be used downstream.
    """

    @abstractmethod
    def stream(self) -> AsyncIterator[SensorPayload]:
        ...


class IDetector(ABC):
    """Pure transform: SensorPayload in, ProcessedState out.

    Implementations own validation, engineering calculations, and
    detection logic. No I/O, no side effects beyond scheduling async
    tasks for incident reports.
    """

    @abstractmethod
    def evaluate(self, payload: SensorPayload) -> ProcessedState:
        ...


class IEventBus(ABC):
    """Fanout hub: one publish triggers all subscribers in parallel.

    Subscribers are registered at startup and never removed. The bus
    does not care whether a subscriber writes to a database, a WebSocket,
    or a log file.
    """

    @abstractmethod
    def subscribe(self, handler: Callable[[ProcessedState], Awaitable[None]]) -> None:
        ...

    @abstractmethod
    async def publish(self, state: ProcessedState) -> None:
        ...
