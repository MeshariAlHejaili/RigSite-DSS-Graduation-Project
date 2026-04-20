"""HTTP endpoints for ArUco-based gate angle detection and full-pipeline image ingest."""
from __future__ import annotations

import dataclasses
import logging
import time

from fastapi import APIRouter, File, Form, Request, UploadFile

from core import angle_detector
from core.detection_engine import DetectionEngine
from core.schemas import SensorPayload
from core.sensor_processor import SensorProcessor

router = APIRouter(prefix="/angle", tags=["angle"])
log = logging.getLogger("riglab.angle")

# One dedicated engine for the HTTP ingest path (stateful, survives across requests)
_http_engine = DetectionEngine()
_http_processor = SensorProcessor(_http_engine)


@router.get("/calibrate/status")
async def calibrate_status() -> dict:
    """Return whether the zero-position calibration has been set."""
    return {"calibrated": angle_detector.is_calibrated()}


@router.post("/calibrate/zero")
async def calibrate_zero(image: UploadFile = File(...)) -> dict:
    """Set the current marker pose as the zero reference (gate fully closed)."""
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
    """Detect gate angle from an uploaded image — no DB write, no broadcast."""
    image_bytes = await image.read()
    angle, _ = angle_detector.detect_angle(image_bytes)
    return {
        "gate_angle": angle,
        "detected": angle is not None,
        "calibrated": angle_detector.is_calibrated(),
    }


@router.post("/ingest")
async def ingest_frame(
    request: Request,
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

    payload = SensorPayload(
        timestamp=time.time(),
        pressure1=pressure1,
        pressure2=pressure2,
        flow=flow,
        gate_angle=angle,
        angle_confidence=confidence if confidence is not None else 0.0,
        device_health={
            "pressure_sensor_ok": pressure_sensor_ok,
            "flow_sensor_ok": flow_sensor_ok,
            "camera_ok": camera_ok,
        },
    )

    state = _http_processor.evaluate(payload)
    await request.app.state.bus.publish(state)

    log.info(
        "ingest_frame angle=%.2f state=%s calibrated=%s",
        angle if angle is not None else -1.0,
        state.state,
        angle_detector.is_calibrated(),
    )
    return {**dataclasses.asdict(state), "calibrated": angle_detector.is_calibrated()}
