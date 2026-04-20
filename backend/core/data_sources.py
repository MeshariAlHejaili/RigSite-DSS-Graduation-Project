"""Concrete IDataSource implementations.

Both sources produce identical SensorPayload streams. The pipeline
cannot tell them apart — that is the point.

WebSocketDataSource   — wraps a live FastAPI WebSocket connection.
SimulatorDataSource   — generates synthetic payloads from scenario functions.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from core import angle_detector
from core.interfaces import IDataSource
from core.schemas import SensorPayload
from core import simulator_scenarios

SimulatorMode = Literal["normal", "kick", "loss"]

log = logging.getLogger("riglab.sources")

_SCENARIO_FNS = {
    "normal": simulator_scenarios.normal,
    "kick": simulator_scenarios.kick,
    "loss": simulator_scenarios.loss,
}


def _decode_base64_frame(raw_value: object) -> bytes | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None

    encoded = raw_value.strip()
    if encoded.startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]

    try:
        return base64.b64decode(encoded, validate=True)
    except Exception:
        return None


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
                gate_angle = raw.get("gate_angle")
                angle_confidence = float(raw.get("angle_confidence", 1.0))
                angle_mode = angle_detector.normalize_mode(raw.get("angle_mode"))
                angle_warning = raw.get("angle_warning")
                viewpoint_consistent = raw.get("viewpoint_consistent")
                camera_calibrated = bool(raw.get("camera_calibrated", False))

                if gate_angle is None:
                    image_bytes = (
                        _decode_base64_frame(raw.get("image_base64"))
                        or _decode_base64_frame(raw.get("frame_base64"))
                        or _decode_base64_frame(raw.get("image"))
                    )
                    if image_bytes is not None:
                        result = angle_detector.detect_angle(image_bytes, mode=angle_mode)
                        gate_angle = result.angle
                        angle_confidence = result.confidence
                        angle_warning = result.warning
                        viewpoint_consistent = result.viewpoint_consistent
                        camera_calibrated = result.camera_calibrated

                        if not result.detected:
                            device_health = raw.get("device_health", {})
                            device_health["camera_ok"] = False
                            raw["device_health"] = device_health

                yield SensorPayload(
                    pressure1=raw["pressure1"],
                    pressure2=raw["pressure2"],
                    flow=raw["flow"],
                    gate_angle=gate_angle,
                    timestamp=raw["timestamp"],
                    angle_confidence=angle_confidence,
                    angle_mode=angle_mode,
                    angle_warning=angle_warning,
                    viewpoint_consistent=viewpoint_consistent,
                    camera_calibrated=camera_calibrated,
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
                angle_mode=angle_detector.normalize_mode(raw.get("angle_mode")),
                angle_warning=raw.get("angle_warning"),
                viewpoint_consistent=raw.get("viewpoint_consistent"),
                camera_calibrated=bool(raw.get("camera_calibrated", False)),
                device_health=raw.get("device_health", {}),
            )
            await asyncio.sleep(self._interval)
