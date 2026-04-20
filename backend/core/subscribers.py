"""Event bus subscribers for persistence and WebSocket fan-out."""
from __future__ import annotations

import datetime
import json
import logging

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from core.schemas import ProcessedState, processed_state_to_payload
from utils import database

log = logging.getLogger("riglab.subscribers")


def _parse_iso_datetime(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(datetime.timezone.utc)


class DatabaseWriter:
    """Writes one ProcessedState per call into the telemetry table."""

    async def handle(self, state: ProcessedState) -> None:
        pool = database.get_pool()
        ts = datetime.datetime.fromtimestamp(state.timestamp, tz=datetime.timezone.utc)
        processed_at = _parse_iso_datetime(state.processed_at)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO telemetry (
                    timestamp, pressure1, pressure2, flow, gate_angle,
                    pressure_diff, expected_flow, flow_deviation, mud_weight,
                    normal_mud_weight, mud_weight_with_cuttings, viscosity,
                    display_mud_weight, angle_deviation, mud_weight_deviation_pct,
                    baseline_angle, baseline_mud_weight, state, decision_conf,
                    sensor_status, detection_mode, processed_at, device_health
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12,
                    $13, $14, $15,
                    $16, $17, $18, $19,
                    $20, $21, $22, $23
                )
                """,
                ts,
                float(state.pressure1),
                float(state.pressure2),
                float(state.flow),
                float(state.gate_angle) if state.gate_angle is not None else None,
                float(state.pressure_diff),
                float(state.expected_flow),
                float(state.flow_deviation_pct),
                float(state.mud_weight) if state.mud_weight is not None else None,
                float(state.normal_mud_weight) if state.normal_mud_weight is not None else None,
                float(state.mud_weight_with_cuttings) if state.mud_weight_with_cuttings is not None else None,
                float(state.viscosity) if state.viscosity is not None else None,
                state.display_mud_weight,
                float(state.angle_deviation) if state.angle_deviation is not None else None,
                float(state.mud_weight_deviation_pct) if state.mud_weight_deviation_pct is not None else None,
                float(state.baseline_angle) if state.baseline_angle is not None else None,
                float(state.baseline_mud_weight) if state.baseline_mud_weight is not None else None,
                state.state,
                float(state.decision_confidence),
                state.sensor_status,
                state.detection_mode,
                processed_at,
                json.dumps(state.device_health),
            )


class WebSocketBroadcaster:
    """Maintains the set of live dashboard connections and fans out states."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def add(self, ws: WebSocket) -> None:
        self._connections.add(ws)

    def remove(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def handle(self, state: ProcessedState) -> None:
        if not self._connections:
            return

        payload = json.dumps(processed_state_to_payload(state))
        dead: set[WebSocket] = set()

        for ws in list(self._connections):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                else:
                    dead.add(ws)
            except Exception:
                dead.add(ws)

        self._connections.difference_update(dead)
        if dead:
            log.debug("removed %d stale live connections", len(dead))
