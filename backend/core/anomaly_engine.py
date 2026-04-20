from __future__ import annotations

import asyncio
import datetime
import time
from collections import deque
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Awaitable, Callable

from core.classifier import classify_deviation
from reports.generator import incident_pdf

TransitionHandler = Callable[[dict], Awaitable[None] | None]

_ACTIVE_ENGINE: ContextVar["AnomalyEngine | None"] = ContextVar("active_anomaly_engine", default=None)
_INCIDENT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "generated"


class AnomalyEngine:
    def __init__(self, on_transition: TransitionHandler | None = None) -> None:
        self._window = 1
        self._history: deque[float] = deque(maxlen=1)
        self._last_state = "NORMAL"
        self._pending_transition: str | None = None
        self._on_transition = on_transition
        self.last_evaluation_duration_ms = 0.0

    def _resize(self, window: int) -> None:
        window = max(1, int(window))
        if window == self._window and self._history.maxlen == window:
            return
        self._window = window
        self._history = deque(list(self._history)[-window:], maxlen=window)

    def evaluate(self, deviation_pct: float, threshold: float, window: int) -> str:
        started_at = time.time()

        self._resize(window)
        self._history.append(float(deviation_pct))
        if len(self._history) < self._window:
            next_state = "NORMAL"
        else:
            states = [classify_deviation(value, threshold) for value in self._history]
            if all(state == "KICK_RISK" for state in states):
                next_state = "KICK_RISK"
            elif all(state == "LOSS_RISK" for state in states):
                next_state = "LOSS_RISK"
            else:
                next_state = "NORMAL"

        if self._last_state == "NORMAL" and next_state in {"KICK_RISK", "LOSS_RISK"}:
            self._pending_transition = next_state

        self._last_state = next_state
        finished_at = time.time()
        self.last_evaluation_duration_ms = round((finished_at - started_at) * 1000.0, 6)
        return next_state

    def consume_transition(self) -> str | None:
        transition = self._pending_transition
        self._pending_transition = None
        return transition

    def get_transition_handler(self) -> TransitionHandler | None:
        return self._on_transition


def _row_for_incident_report(state: dict) -> dict:
    record = dict(state)
    timestamp = record.get("timestamp")
    if isinstance(timestamp, (int, float)):
        record["timestamp"] = (
            datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    record.setdefault("processed_at", datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"))
    return record


def _incident_snapshot_path(state: dict) -> Path:
    timestamp = state.get("processed_at")
    safe_timestamp = str(timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()).replace(":", "-")
    return _INCIDENT_OUTPUT_DIR / f"incident_{state['state'].lower()}_{safe_timestamp}.pdf"


def _write_incident_snapshot(state: dict) -> Path:
    _INCIDENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _incident_snapshot_path(state)
    path.write_bytes(incident_pdf([_row_for_incident_report(state)]))
    return path


async def _default_transition_handler(state: dict) -> None:
    await asyncio.to_thread(_write_incident_snapshot, state)


def _schedule_callback(callback: TransitionHandler, state: dict) -> None:
    maybe_awaitable = callback(state)
    if maybe_awaitable is None:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(maybe_awaitable)
    except RuntimeError:
        asyncio.run(maybe_awaitable)


def schedule_transition_actions(state: dict) -> None:
    engine = _ACTIVE_ENGINE.get()
    if engine is None:
        return

    transition_state = engine.consume_transition()
    if transition_state is None:
        return

    incident_state = dict(state)
    incident_state["state"] = transition_state

    handler = engine.get_transition_handler()
    if handler is not None:
        _schedule_callback(handler, incident_state)
        return

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_default_transition_handler(incident_state))
    except RuntimeError:
        _write_incident_snapshot(incident_state)


def set_active_engine(engine: AnomalyEngine) -> Token:
    return _ACTIVE_ENGINE.set(engine)


def reset_active_engine(token: Token) -> None:
    _ACTIVE_ENGINE.reset(token)


def get_active_engine() -> AnomalyEngine | None:
    return _ACTIVE_ENGINE.get()


def evaluate(deviation_pct: float, threshold: float, window: int) -> str:
    engine = _ACTIVE_ENGINE.get()
    if engine is None:
        engine = AnomalyEngine()
    return engine.evaluate(deviation_pct, threshold, window)
