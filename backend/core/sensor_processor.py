"""SensorProcessor — the IDetector implementation.

Owns the full processing pipeline for one sensor payload:
  1. Input validation
  2. Engineering calculations (pressure diff, expected flow, density)
  3. Detection via an injected DetectionEngine
  4. Construction of the immutable ProcessedState output
  5. Fire-and-forget incident report on NORMAL → alarm transition

The DetectionEngine is injected at construction time. SensorProcessor has
no knowledge of where payloads come from or where ProcessedState goes.
"""
from __future__ import annotations

import datetime
from collections.abc import Callable

from utils import engineering
from utils.config import get_detection_settings, get_pete_constants, interpolate_expected_flow
from core.detection_engine import DetectionEngine, schedule_incident_report
from core.interfaces import IDetector
from core.schemas import ProcessedState, SensorPayload


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sensor_fault_from_health(device_health: dict) -> str:
    pressure_fault = not device_health.get("pressure_sensor_ok", True)
    flow_fault = not device_health.get("flow_sensor_ok", True)
    camera_fault = not device_health.get("camera_ok", True)
    fault_count = sum((pressure_fault, flow_fault, camera_fault))

    if fault_count == 0:
        return "ALL_OK"
    if fault_count > 1:
        return "MULTI_FAULT"
    if pressure_fault:
        return "PRESSURE_FAULT"
    if flow_fault:
        return "FLOW_FAULT"
    return "CAMERA_FAULT"


def _fault_from_validation(fault_fields: set[str], device_health: dict) -> str:
    sensor_status = _sensor_fault_from_health(device_health)
    if sensor_status != "ALL_OK":
        return sensor_status
    if {"pressure1", "pressure2"} & fault_fields:
        return "PRESSURE_FAULT"
    if "flow" in fault_fields:
        return "FLOW_FAULT"
    if {"gate_angle", "angle_confidence"} & fault_fields:
        return "CAMERA_FAULT"
    return "MULTI_FAULT"


class SensorProcessor(IDetector):
    """Stateful processor bound to a single DetectionEngine instance.

    One SensorProcessor per ingestion session ensures streak counters are
    isolated between concurrent WebSocket connections and the simulator.

    Args:
        engine: The DetectionEngine this processor drives. Callers are
            responsible for constructing and owning the engine.
        get_settings: Optional override for reading detection settings,
            primarily for testing. Defaults to config.get_detection_settings.
        get_pete: Optional override for reading PETE constants,
            primarily for testing. Defaults to config.get_pete_constants.
    """

    def __init__(
        self,
        engine: DetectionEngine,
        get_settings: Callable[[], dict] | None = None,
        get_pete: Callable[[], dict] | None = None,
    ) -> None:
        self._engine = engine
        self._get_settings = get_settings or get_detection_settings
        self._get_pete = get_pete or get_pete_constants

    def evaluate(self, payload: SensorPayload) -> ProcessedState:
        pete = self._get_pete()
        detection_settings = self._get_settings()

        device_health = payload.device_health or {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        }

        # --- Validation ---
        faults: set[str] = set()
        if payload.pressure1 is None or not (0.0 <= payload.pressure1 <= 20.0):
            faults.add("pressure1")
        if payload.pressure2 is None or not (0.0 <= payload.pressure2 <= 20.0):
            faults.add("pressure2")
        if payload.flow is None or not (0.0 <= payload.flow <= 30.0):
            faults.add("flow")
        if payload.gate_angle is not None and not (0.0 <= payload.gate_angle <= 90.0):
            faults.add("gate_angle")
        if not (0.0 <= payload.angle_confidence <= 1.0):
            faults.add("angle_confidence")

        if faults:
            return ProcessedState(
                timestamp=payload.timestamp,
                pressure1=payload.pressure1 or 0.0,
                pressure2=payload.pressure2 or 0.0,
                flow=payload.flow or 0.0,
                gate_angle=payload.gate_angle,
                pressure_diff=0.0,
                expected_flow=0.0,
                flow_deviation_pct=0.0,
                density=None,
                angle_deviation=None,
                density_deviation_pct=None,
                baseline_angle=None,
                state="SENSOR_FAULT",
                decision_confidence=0.0,
                sensor_status=_fault_from_validation(faults, device_health),
                detection_mode=detection_settings.get("detection_mode", "angle_only"),
                processed_at=_now_iso(),
                device_health=device_health,
            )

        # --- Engineering calculations (display only; not used in detection) ---
        sensor_status = _sensor_fault_from_health(device_health)
        pressure_diff = round(payload.pressure1 - payload.pressure2, 4)
        expected_flow = interpolate_expected_flow(
            payload.gate_angle,
            flow_baseline=float(pete["flow_baseline"]),
        )
        if expected_flow == 0:
            flow_deviation_pct = 0.0
        else:
            flow_deviation_pct = round(
                ((payload.flow - expected_flow) / expected_flow) * 100.0, 4
            )

        # --- Density (angle_density mode only) ---
        mode = detection_settings.get("detection_mode", "angle_only")
        delta_h = float(detection_settings.get("delta_h", 1.0))
        density = (
            engineering.calculate_density(pressure_diff, delta_h)
            if mode == "angle_density"
            else None
        )

        # --- Detection ---
        self._engine.sync_baseline_from_config(detection_settings)
        det_state = self._engine.evaluate(payload.gate_angle, density, mode)
        display = self._engine.get_display_state()

        processed_state = ProcessedState(
            timestamp=payload.timestamp,
            pressure1=payload.pressure1,
            pressure2=payload.pressure2,
            flow=payload.flow,
            gate_angle=payload.gate_angle,
            pressure_diff=pressure_diff,
            expected_flow=expected_flow,
            flow_deviation_pct=flow_deviation_pct,
            density=density,
            angle_deviation=display["angle_deviation"],
            density_deviation_pct=display["density_deviation_pct"],
            baseline_angle=display["baseline_angle"],
            state=det_state,
            decision_confidence=round(float(payload.angle_confidence), 4),
            sensor_status=sensor_status,
            detection_mode=mode,
            processed_at=_now_iso(),
            device_health=device_health,
        )

        # --- Transition: fire-and-forget incident PDF ---
        transition = self._engine.consume_transition()
        if transition is not None:
            import asyncio
            from dataclasses import asdict
            incident = {**asdict(processed_state), "state": transition}
            asyncio.ensure_future(schedule_incident_report(incident))

        return processed_state
