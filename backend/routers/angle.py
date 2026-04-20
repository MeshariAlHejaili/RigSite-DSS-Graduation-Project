"""HTTP endpoints for ArUco-based gate angle detection and full-pipeline image ingest."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, File, Form, UploadFile

import angle_detector
import config as cfg
import detection_engine
from detection_engine import DetectionEngine
from processing import process_payload
from routers.websocket import persist_and_broadcast

router = APIRouter(prefix="/angle", tags=["angle"])
log = logging.getLogger("riglab.angle")

_http_engine = DetectionEngine()


@router.get("/calibrate/status")
async def calibrate_status() -> dict:
    """Return whether the zero-position calibration has been set."""
    return {"calibrated": angle_detector.is_calibrated()}


@router.post("/calibrate/zero")
async def calibrate_zero(image: UploadFile = File(...)) -> dict:
    """Set the current marker pose as the zero reference (gate fully closed).

    Upload a photo of the gate in the fully-closed position. After this call,
    detect and ingest endpoints report angles relative to this reference.
    The calibration is persisted to disk and survives server restarts.
    """
    image_bytes = await image.read()
    success, message = angle_detector.calibrate_zero(image_bytes)
    return {"success": success, "message": message}


@router.delete("/calibrate/zero")
async def clear_calibration() -> dict:
    """Remove the stored zero calibration (resets to uncalibrated mode)."""
    angle_detector.clear_calibration()
    return {"success": True, "message": "Calibration cleared"}


@router.post("/detect")
async def detect_angle_endpoint(image: UploadFile = File(...)) -> dict:
    """Detect gate angle from an uploaded image.

    Lightweight endpoint for testing — no DB write, no broadcast.
    """
    image_bytes = await image.read()
    angle, _ = angle_detector.detect_angle(image_bytes)
    return {
        "gate_angle": angle,
        "detected": angle is not None,
        "calibrated": angle_detector.is_calibrated(),
    }


@router.post("/ingest")
async def ingest_frame(
    image: UploadFile = File(...),
    pressure1: float = Form(...),
    pressure2: float = Form(...),
    flow: float = Form(...),
    pressure_sensor_ok: bool = Form(True),
    flow_sensor_ok: bool = Form(True),
) -> dict:
    """Full ingest: image + sensor readings → angle detection → pipeline → DB + broadcast."""
    image_bytes = await image.read()
    angle, confidence = angle_detector.detect_angle(image_bytes)
    camera_ok = angle is not None

    raw: dict = {
        "timestamp": time.time(),
        "pressure1": pressure1,
        "pressure2": pressure2,
        "flow": flow,
        "gate_angle": angle,
        "angle_confidence": confidence if confidence is not None else 0.0,
        "device_health": {
            "pressure_sensor_ok": pressure_sensor_ok,
            "flow_sensor_ok": flow_sensor_ok,
            "camera_ok": camera_ok,
        },
    }

    token = detection_engine.set_active_engine(_http_engine)
    try:
        state = process_payload(raw, cfg.get_pete_constants(), cfg.get_detection_settings())
    finally:
        detection_engine.reset_active_engine(token)

    await persist_and_broadcast(state)
    log.info(
        "ingest_frame angle=%.2f state=%s calibrated=%s",
        angle if angle is not None else -1.0,
        state.get("state"),
        angle_detector.is_calibrated(),
    )
    return {**state, "calibrated": angle_detector.is_calibrated()}
