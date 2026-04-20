"""WebSocket transport layer for ingest and normalized live telemetry."""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.data_sources import WebSocketDataSource
from core.detection_engine import DetectionEngine
from core.pipeline import IngestionPipeline
from core.sensor_processor import SensorProcessor
from core.subscribers import WebSocketBroadcaster
from utils import database

router = APIRouter()
log = logging.getLogger("riglab.ws")


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

    bus = websocket.app.state.bus
    detector = SensorProcessor(DetectionEngine())
    source = WebSocketDataSource(websocket)
    pipeline = IngestionPipeline(detector=detector, bus=bus)

    session_id = await _create_session()
    log.info("ingest connected (session=%s)", session_id)

    try:
        await pipeline.run(source)
    except WebSocketDisconnect:
        pass
    finally:
        await _close_session(session_id)
        log.info("ingest disconnected (session=%s)", session_id)


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    """Subscribe to normalized live telemetry payloads."""
    broadcaster: WebSocketBroadcaster = websocket.app.state.broadcaster
    await websocket.accept()
    broadcaster.add(websocket)
    log.info("live connected (total=%d)", broadcaster.connection_count)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.remove(websocket)
        log.info("live disconnected (total=%d)", broadcaster.connection_count)
