"""HTTP endpoints for ArUco-based gate angle detection and image ingest."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from core import angle_detector
from core.detection_engine import DetectionEngine
from core.schemas import SensorPayload, processed_state_to_payload
from core.sensor_processor import SensorProcessor

router = APIRouter(prefix="/angle", tags=["angle"])
log = logging.getLogger("riglab.angle")

_http_engine = DetectionEngine()
_http_processor = SensorProcessor(_http_engine)


def _normalize_mode(mode: str | None) -> str:
    return angle_detector.normalize_mode(mode)


async def _collect_images(images: list[UploadFile]) -> list[bytes]:
    batch: list[bytes] = []
    for item in images:
        content = await item.read()
        if content:
            batch.append(content)
    return batch


def _extract_uploads_from_form(form) -> list[UploadFile]:
    uploads: list[UploadFile] = []
    seen_ids: set[int] = set()

    for key in ("images", "image", "images[]", "image[]"):
        for item in form.getlist(key):
            if isinstance(item, (UploadFile, StarletteUploadFile)):
                marker = id(item)
                if marker not in seen_ids:
                    uploads.append(item)
                    seen_ids.add(marker)

    return uploads


@router.get("/calibrate/status")
async def calibrate_status() -> dict:
    return {
        "calibrated": angle_detector.is_calibrated(),
        "zero_calibration": angle_detector.get_zero_calibration_status(),
        "camera_calibration": angle_detector.get_camera_calibration_status(),
    }


@router.post("/camera-calibration/upload")
async def upload_camera_calibration(file: UploadFile = File(...)) -> dict:
    payload = await file.read()
    success, message = angle_detector.set_camera_calibration_from_bytes(payload)
    return {
        "success": success,
        "message": message,
        "camera_calibration": angle_detector.get_camera_calibration_status(),
    }


@router.delete("/camera-calibration")
async def clear_camera_calibration() -> dict:
    angle_detector.clear_camera_calibration()
    return {
        "success": True,
        "message": "Camera calibration cleared",
        "camera_calibration": angle_detector.get_camera_calibration_status(),
    }


@router.post("/calibrate/zero")
async def calibrate_zero(
    request: Request,
) -> dict:
    form = await request.form()
    mode = _normalize_mode(str(form.get("mode") or "mounted"))
    uploads = _extract_uploads_from_form(form)

    if not uploads:
        raise HTTPException(status_code=400, detail="At least one calibration image is required.")

    batch = await _collect_images(uploads)
    result = angle_detector.calibrate_zero(batch, mode=mode)
    result["camera_calibration"] = angle_detector.get_camera_calibration_status()
    return result


@router.delete("/calibrate/zero")
async def clear_calibration() -> dict:
    angle_detector.clear_calibration()
    return {
        "success": True,
        "message": "Calibration cleared",
        "zero_calibration": angle_detector.get_zero_calibration_status(),
        "camera_calibration": angle_detector.get_camera_calibration_status(),
    }


@router.post("/detect")
async def detect_angle_endpoint(
    image: UploadFile = File(...),
    mode: str = Form("handheld"),
) -> dict:
    image_bytes = await image.read()
    result = angle_detector.detect_angle(image_bytes, mode=mode)
    payload = result.to_dict()
    payload["zero_calibration"] = angle_detector.get_zero_calibration_status()
    payload["camera_calibration"] = angle_detector.get_camera_calibration_status()
    return payload


@router.post("/ingest")
async def ingest_frame(
    request: Request,
    image: UploadFile = File(...),
    pressure1: float = Form(...),
    pressure2: float = Form(...),
    flow: float = Form(...),
    mode: str = Form("handheld"),
    pressure_sensor_ok: bool = Form(True),
    flow_sensor_ok: bool = Form(True),
) -> dict:
    image_bytes = await image.read()
    normalized_mode = _normalize_mode(mode)
    result = angle_detector.detect_angle(image_bytes, mode=normalized_mode)
    camera_ok = result.detected

    payload = SensorPayload(
        timestamp=time.time(),
        pressure1=pressure1,
        pressure2=pressure2,
        flow=flow,
        gate_angle=result.angle,
        angle_confidence=result.confidence,
        angle_mode=normalized_mode,
        angle_warning=result.warning,
        viewpoint_consistent=result.viewpoint_consistent,
        camera_calibrated=result.camera_calibrated,
        device_health={
            "pressure_sensor_ok": pressure_sensor_ok,
            "flow_sensor_ok": flow_sensor_ok,
            "camera_ok": camera_ok,
        },
    )

    state = _http_processor.evaluate(payload)
    await request.app.state.bus.publish(state)

    log.info(
        "ingest_frame angle=%.2f state=%s calibrated=%s mode=%s",
        result.angle if result.angle is not None else -1.0,
        state.state,
        angle_detector.is_calibrated(),
        normalized_mode,
    )
    return {
        **processed_state_to_payload(state),
        "detected": result.detected,
        "confidence": result.confidence,
        "warning": result.warning,
        "viewpoint_consistent": result.viewpoint_consistent,
        "camera_calibrated": result.camera_calibrated,
        "zero_calibration": angle_detector.get_zero_calibration_status(),
        "camera_calibration": angle_detector.get_camera_calibration_status(),
    }
