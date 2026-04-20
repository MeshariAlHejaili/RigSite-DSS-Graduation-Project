"""Concrete IDataSource implementations.

Both sources produce identical SensorPayload streams. The pipeline
cannot tell them apart — that is the point.

WebSocketDataSource   — wraps a live FastAPI WebSocket connection.
SimulatorDataSource   — generates synthetic payloads from scenario functions.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from interfaces import IDataSource
from schemas import SensorPayload
import simulator_scenarios

SimulatorMode = Literal["normal", "kick", "loss"]

log = logging.getLogger("riglab.sources")

_SCENARIO_FNS = {
    "normal": simulator_scenarios.normal,
    "kick": simulator_scenarios.kick,
    "loss": simulator_scenarios.loss,
}


class WebSocketDataSource(IDataSource):
    """Reads JSON frames from an accepted WebSocket and yields SensorPayloads.

    Invalid JSON frames are logged and skipped; the WebSocketDisconnect
    exception propagates naturally so the router can clean up.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def stream(self) -> AsyncIterator[SensorPayload]:
        while True:
            try:
                raw = await self._ws.receive_json()
            except Exception:
                if self._ws.client_state != WebSocketState.CONNECTED:
                    return
                log.warning("invalid ingest payload — skipping frame")
                await self._ws.send_json({"error": "invalid_payload"})
                continue

            try:
                yield SensorPayload(
                    pressure1=raw["pressure1"],
                    pressure2=raw["pressure2"],
                    flow=raw["flow"],
                    gate_angle=raw.get("gate_angle"),
                    timestamp=raw["timestamp"],
                    angle_confidence=float(raw.get("angle_confidence", 1.0)),
                    device_health=raw.get("device_health", {}),
                )
            except (KeyError, TypeError, ValueError) as exc:
                log.warning("malformed payload fields (%s) — skipping frame", exc)
                await self._ws.send_json({"error": "malformed_payload"})


class SimulatorDataSource(IDataSource):
    """Generates synthetic SensorPayloads from a named scenario at a fixed interval.

    The active mode can be changed at runtime between yields by setting
    the `mode` property. The sample index advances monotonically so
    waveforms don't reset on mode changes.
    """

    def __init__(self, mode: SimulatorMode = "normal", interval: float = 1.0) -> None:
        self._mode: SimulatorMode = mode
        self._interval = interval
        self._index = 0

    @property
    def mode(self) -> SimulatorMode:
        return self._mode

    @mode.setter
    def mode(self, value: SimulatorMode) -> None:
        if value not in _SCENARIO_FNS:
            raise ValueError(f"Unknown simulator mode: {value!r}")
        self._mode = value

    async def stream(self) -> AsyncIterator[SensorPayload]:
        while True:
            raw = _SCENARIO_FNS[self._mode](self._index)
            self._index += 1
            yield SensorPayload(
                pressure1=raw["pressure1"],
                pressure2=raw["pressure2"],
                flow=raw["flow"],
                gate_angle=raw.get("gate_angle"),
                timestamp=raw["timestamp"],
                angle_confidence=float(raw.get("angle_confidence", 1.0)),
                device_health=raw.get("device_health", {}),
            )
            await asyncio.sleep(self._interval)
