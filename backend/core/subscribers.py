"""Event bus subscribers — independent consumers of ProcessedState.

DatabaseWriter      — persists every state to the telemetry table.
WebSocketBroadcaster — pushes every state to all connected /ws/live clients.

Both are registered on the InMemoryEventBus at startup. They run in
parallel on each publish() call — a slow DB insert never delays the
broadcast, and a broadcast failure never skips the DB write.
"""
from __future__ import annotations

import datetime
import json
import logging
from dataclasses import asdict

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from utils import database
from core.schemas import ProcessedState

log = logging.getLogger("riglab.subscribers")


class DatabaseWriter:
    """Writes one ProcessedState per call into the telemetry table."""

    async def handle(self, state: ProcessedState) -> None:
        pool = database.get_pool()
        ts = datetime.datetime.fromtimestamp(state.timestamp, tz=datetime.timezone.utc)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO telemetry (
                    timestamp, pressure1, pressure2, flow, gate_angle,
                    pressure_diff, expected_flow, flow_deviation, state,
                    decision_conf, sensor_status, device_health
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                ts,
                float(state.pressure1),
                float(state.pressure2),
                float(state.flow),
                float(state.gate_angle) if state.gate_angle is not None else None,
                float(state.pressure_diff),
                float(state.expected_flow),
                float(state.flow_deviation_pct),
                state.state,
                float(state.decision_confidence),
                state.sensor_status,
                json.dumps(state.device_health),
            )


class WebSocketBroadcaster:
    """Maintains the set of live dashboard connections and fans out states.

    The /ws/live router calls add() on connect and remove() on disconnect.
    handle() is registered on the event bus at startup.
    """

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

        payload = json.dumps(asdict(state))
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
