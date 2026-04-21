"""HTTP ingest endpoint for Raspberry Pi sensor + camera data.

The Pi POSTs JSON every second containing pressure1, pressure2, flow,
and an optional base64-encoded JPEG. This router:
  1. Auto-creates a database session on the first request.
  2. Decodes the image and runs ArUco angle detection.
  3. Builds a SensorPayload and pushes it through the shared pipeline
     (SensorProcessor → event bus → DatabaseWriter + WebSocketBroadcaster).
  4. Returns the full ProcessedState so the Pi can log it locally.

Session lifecycle:
  POST /api/v1/pi/ingest      – feed one sample (creates session lazily)
  POST /api/v1/pi/session/stop – close the active session (call on button-release)
"""
from __future__ import annotations

import base64
import logging
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from core import angle_detector
from core.detection_engine import DetectionEngine
from core.schemas import SensorPayload, processed_state_to_payload
from core.sensor_processor import SensorProcessor
from utils import database

router = APIRouter(prefix="/pi", tags=["pi"])
log = logging.getLogger("riglab.pi_ingest")

# One stateful processor for the Pi – persists streak counters and baseline
# across the lifetime of the backend process, just like the WebSocket path.
_pi_engine = DetectionEngine()
_pi_processor = SensorProcessor(_pi_engine)


class PiPayload(BaseModel):
    pressure1: float = Field(..., ge=0.0, le=20.0, description="Upstream pressure (PSI)")
    pressure2: float = Field(..., ge=0.0, le=20.0, description="Downstream pressure (PSI)")
    flow: float = Field(..., ge=0.0, le=30.0, description="Flow rate (GPM)")
    image_b64: str | None = Field(default=None, description="Base64-encoded JPEG from PiCamera")
    timestamp: float | None = Field(default=None, description="Unix epoch seconds; defaults to server time")


async def _ensure_pi_session(app) -> int:
    """Return the active Pi session id, creating one if none exists."""
    if getattr(app.state, "pi_session_id", None) is None:
        pool = database.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("INSERT INTO sessions DEFAULT VALUES RETURNING id")
        app.state.pi_session_id = int(row["id"])
        log.info("Pi session created (id=%d)", app.state.pi_session_id)
    return app.state.pi_session_id


async def _close_pi_session(app) -> int | None:
    """Close the active Pi session. Returns the closed session id or None."""
    session_id = getattr(app.state, "pi_session_id", None)
    if session_id is None:
        return None
    pool = database.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET ended_at = NOW() WHERE id = $1 AND ended_at IS NULL",
            session_id,
        )
    app.state.pi_session_id = None
    log.info("Pi session closed (id=%d)", session_id)
    return session_id


@router.post("/ingest")
async def pi_ingest(payload: PiPayload, request: Request) -> dict:
    """Receive one sensor sample from the Raspberry Pi and run the full pipeline."""
    await _ensure_pi_session(request.app)

    ts = payload.timestamp or time.time()

    # --- Angle detection from camera image ---
    gate_angle: float | None = None
    confidence: float = 1.0
    warning: str | None = None
    viewpoint_consistent: bool | None = None
    camera_calibrated: bool = angle_detector.is_calibrated()
    camera_ok: bool = False

    if payload.image_b64:
        try:
            image_bytes = base64.b64decode(payload.image_b64)
        except Exception:
            log.warning("Invalid base64 image payload; skipping angle detection")
            image_bytes = None

        if image_bytes:
            detection = angle_detector.detect_angle(image_bytes, mode="mounted")
            gate_angle = detection.angle
            confidence = detection.confidence
            warning = detection.warning
            viewpoint_consistent = detection.viewpoint_consistent
            camera_calibrated = detection.camera_calibrated
            camera_ok = detection.detected

    # --- Build and evaluate SensorPayload ---
    sensor_payload = SensorPayload(
        timestamp=ts,
        pressure1=payload.pressure1,
        pressure2=payload.pressure2,
        flow=payload.flow,
        gate_angle=gate_angle,
        angle_confidence=confidence,
        angle_mode="mounted",
        angle_warning=warning,
        viewpoint_consistent=viewpoint_consistent,
        camera_calibrated=camera_calibrated,
        device_health={
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": camera_ok,
        },
    )

    state = _pi_processor.evaluate(sensor_payload)
    await request.app.state.bus.publish(state)

    log.info(
        "pi_ingest | angle=%s state=%s P1=%.4f P2=%.4f flow=%.3f GPM",
        f"{gate_angle:.2f}°" if gate_angle is not None else "None",
        state.state,
        payload.pressure1,
        payload.pressure2,
        payload.flow,
    )

    result = processed_state_to_payload(state)
    if result.get("gate_angle") is None:
        result["gate_angle"] = -99.0
    return result


@router.post("/session/stop")
async def pi_session_stop(request: Request) -> dict:
    """Signal that the Pi has stopped recording; closes the active session."""
    closed_id = await _close_pi_session(request.app)
    if closed_id is None:
        return {"status": "no_active_session"}
    return {"status": "stopped", "session_id": closed_id}


@router.get("/status")
async def pi_status(request: Request) -> dict:
    """Quick health-check the Pi can call to verify the backend is reachable."""
    session_id = getattr(request.app.state, "pi_session_id", None)
    return {
        "backend": "online",
        "pi_session_active": session_id is not None,
        "pi_session_id": session_id,
        "angle_calibrated": angle_detector.is_calibrated(),
    }
