from __future__ import annotations

import datetime
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import anomaly_engine
import config as cfg
import database
from anomaly_engine import AnomalyEngine
from processing import process_payload

router = APIRouter()
log = logging.getLogger("riglab.ws")

ingest_connections: set[WebSocket] = set()
live_connections: set[WebSocket] = set()
ingest_sessions: dict[WebSocket, int] = {}


async def _broadcast(data: str) -> None:
    dead_connections: set[WebSocket] = set()
    for websocket in list(live_connections):
        try:
            await websocket.send_text(data)
        except Exception:
            dead_connections.add(websocket)
    live_connections.difference_update(dead_connections)


async def _db_write(state: dict) -> None:
    pool = database.get_pool()
    timestamp = datetime.datetime.fromtimestamp(state["timestamp"], tz=datetime.timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO telemetry (
                timestamp, pressure1, pressure2, flow, gate_angle, angle_confidence,
                pressure_diff, expected_flow, flow_deviation, state, decision_conf,
                sensor_status, device_health
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
            timestamp,
            float(state["pressure1"]),
            float(state["pressure2"]),
            float(state["flow"]),
            float(state["gate_angle"]) if state.get("gate_angle") is not None else None,
            float(state.get("angle_confidence") or 0.0),
            float(state["pressure_diff"]),
            float(state["expected_flow"]),
            float(state["flow_deviation_pct"]),
            state["state"],
            float(state["decision_confidence"]),
            state["sensor_status"],
            json.dumps(state.get("device_health", {})),
        )


async def persist_and_broadcast(state: dict) -> None:
    try:
        await _db_write(state)
    except Exception as exc:
        log.error("DB write failed: %s", exc)
    await _broadcast(json.dumps(state))


async def _create_session() -> int:
    pool = database.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("INSERT INTO sessions DEFAULT VALUES RETURNING id")
    return int(row["id"])


async def _close_session(session_id: int) -> None:
    pool = database.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET ended_at = NOW() WHERE id = $1 AND ended_at IS NULL",
            session_id,
        )


@router.websocket("/ws/ingest")
async def ws_ingest(websocket: WebSocket) -> None:
    await websocket.accept()
    ingest_connections.add(websocket)
    engine = AnomalyEngine()
    session_id = await _create_session()
    ingest_sessions[websocket] = session_id
    log.info("ingest connected (session=%s total=%d)", session_id, len(ingest_connections))

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                raw = json.loads(raw_text)
            except json.JSONDecodeError:
                log.warning("invalid ingest payload: %s", raw_text)
                await websocket.send_json({"error": "invalid_payload"})
                continue

            token = anomaly_engine.set_active_engine(engine)
            try:
                state = process_payload(raw, cfg.get_pete_constants())
            finally:
                anomaly_engine.reset_active_engine(token)

            await persist_and_broadcast(state)
    except WebSocketDisconnect:
        pass
    finally:
        ingest_connections.discard(websocket)
        closed_session_id = ingest_sessions.pop(websocket, None)
        if closed_session_id is not None:
            await _close_session(closed_session_id)
        log.info("ingest disconnected (session=%s total=%d)", closed_session_id, len(ingest_connections))


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    await websocket.accept()
    live_connections.add(websocket)
    log.info("live connected (total=%d)", len(live_connections))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        live_connections.discard(websocket)
        log.info("live disconnected (total=%d)", len(live_connections))
