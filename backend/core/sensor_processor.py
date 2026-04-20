"""SensorProcessor - validation, engineering metrics, and anomaly detection."""
from __future__ import annotations

import datetime
from collections.abc import Callable

from core.detection_engine import DetectionEngine, schedule_incident_report
from core.interfaces import IDetector
from core.schemas import ProcessedState, SensorPayload
from utils import engineering
from utils.config import (
    get_detection_settings,
    get_pete_constants,
    get_system_settings,
    get_viscosity_constants,
    interpolate_expected_flow,
    set_detection_baseline,
)

STARTUP_BASELINE_SAMPLES = 3


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
    """Stateful processor bound to a single DetectionEngine instance."""

    def __init__(
        self,
        engine: DetectionEngine,
        get_settings: Callable[[], dict] | None = None,
        get_pete: Callable[[], dict] | None = None,
        get_system: Callable[[], dict] | None = None,
        get_viscosity: Callable[[], dict] | None = None,
    ) -> None:
        self._engine = engine
        self._get_settings = get_settings or get_detection_settings
        self._get_pete = get_pete or get_pete_constants
        self._get_system = get_system or get_system_settings
        self._get_viscosity = get_viscosity or get_viscosity_constants
        self._startup_baseline_locked = False
        self._startup_baseline_mode: str | None = None
        self._startup_baseline_points: list[tuple[float, float | None]] = []

    def _maybe_initialize_startup_baseline(
        self,
        detection_settings: dict,
        mode: str,
        gate_angle: float | None,
        mud_weight: float | None,
    ) -> dict:
        # Auto-baseline only once when the system has no baseline at startup.
        if self._startup_baseline_locked:
            return detection_settings

        if detection_settings.get("baseline_angle") is not None or detection_settings.get("baseline_mud_weight") is not None:
            self._startup_baseline_locked = True
            self._startup_baseline_points.clear()
            return detection_settings

        if gate_angle is None:
            return detection_settings

        if mode == "angle_mud_weight" and mud_weight is None:
            return detection_settings

        if self._startup_baseline_mode is not None and self._startup_baseline_mode != mode:
            self._startup_baseline_points.clear()

        self._startup_baseline_mode = mode
        self._startup_baseline_points.append((float(gate_angle), float(mud_weight) if mud_weight is not None else None))

        if len(self._startup_baseline_points) < STARTUP_BASELINE_SAMPLES:
            return detection_settings

        baseline_angle = sum(point[0] for point in self._startup_baseline_points) / STARTUP_BASELINE_SAMPLES
        baseline_mud_weight = None
        if mode == "angle_mud_weight":
            mud_weights = [point[1] for point in self._startup_baseline_points if point[1] is not None]
            if len(mud_weights) < STARTUP_BASELINE_SAMPLES:
                return detection_settings
            baseline_mud_weight = sum(mud_weights) / STARTUP_BASELINE_SAMPLES

        set_detection_baseline(baseline_angle=baseline_angle, baseline_mud_weight=baseline_mud_weight)
        self._startup_baseline_locked = True
        self._startup_baseline_points.clear()
        return self._get_settings()

    def evaluate(self, payload: SensorPayload) -> ProcessedState:
        pete = self._get_pete()
        system_settings = self._get_system()
        viscosity_constants = self._get_viscosity()
        detection_settings = self._get_settings()

        device_health = payload.device_health or {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        }
        display_mud_weight = system_settings.get("display_mud_weight", "normal")

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
                mud_weight=None,
                normal_mud_weight=None,
                mud_weight_with_cuttings=None,
                viscosity=None,
                display_mud_weight=display_mud_weight,
                angle_deviation=None,
                mud_weight_deviation_pct=None,
                baseline_angle=None,
                baseline_mud_weight=None,
                state="SENSOR_FAULT",
                decision_confidence=0.0,
                sensor_status=_fault_from_validation(faults, device_health),
                detection_mode=detection_settings.get("detection_mode", "angle_only"),
                angle_mode=payload.angle_mode,
                angle_warning=payload.angle_warning,
                viewpoint_consistent=payload.viewpoint_consistent,
                camera_calibrated=payload.camera_calibrated,
                processed_at=_now_iso(),
                device_health=device_health,
            )

        sensor_status = _sensor_fault_from_health(device_health)
        pressure_diff = round(payload.pressure1 - payload.pressure2, 4)
        if payload.gate_angle is None:
            expected_flow = 0.0
        else:
            expected_flow = interpolate_expected_flow(
                payload.gate_angle,
                flow_baseline=float(pete["flow_baseline"]),
            )
        if expected_flow == 0:
            flow_deviation_pct = 0.0
        else:
            flow_deviation_pct = round(((payload.flow - expected_flow) / expected_flow) * 100.0, 4)

        metrics = engineering.calculate_metrics(
            engineering.EngineeringInputs(
                pressure_diff_psi=pressure_diff,
                delta_h_ft=float(detection_settings.get("delta_h_ft", 1.0)),
                pipe_diameter_m=float(viscosity_constants["pipe_diameter_m"]),
                sensor_spacing_m=float(viscosity_constants["sensor_spacing_m"]),
                fluid_velocity_m_s=float(viscosity_constants["fluid_velocity_m_s"]),
                cuttings_density_ppg=float(pete["cuttings_density"]),
                cuttings_volume_fraction=float(pete["cuttings_volume_fraction"]),
                suspension_factor=float(pete["suspension_factor"]),
                display_mud_weight=display_mud_weight,
            )
        )

        mode = detection_settings.get("detection_mode", "angle_only")
        mud_weight_for_detection = metrics.mud_weight if mode == "angle_mud_weight" else None

        detection_settings = self._maybe_initialize_startup_baseline(
            detection_settings=detection_settings,
            mode=mode,
            gate_angle=payload.gate_angle,
            mud_weight=mud_weight_for_detection,
        )
        mode = detection_settings.get("detection_mode", "angle_only")
        mud_weight_for_detection = metrics.mud_weight if mode == "angle_mud_weight" else None

        self._engine.sync_baseline_from_config(detection_settings)
        det_state = self._engine.evaluate(payload.gate_angle, mud_weight_for_detection, mode)
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
            mud_weight=metrics.mud_weight,
            normal_mud_weight=metrics.normal_mud_weight,
            mud_weight_with_cuttings=metrics.mud_weight_with_cuttings,
            viscosity=metrics.viscosity,
            display_mud_weight=display_mud_weight,
            angle_deviation=display["angle_deviation"],
            mud_weight_deviation_pct=display["mud_weight_deviation_pct"],
            baseline_angle=display["baseline_angle"],
            baseline_mud_weight=display["baseline_mud_weight"],
            state=det_state,
            decision_confidence=round(float(payload.angle_confidence), 4),
            sensor_status=sensor_status,
            detection_mode=mode,
            angle_mode=payload.angle_mode,
            angle_warning=payload.angle_warning,
            viewpoint_consistent=payload.viewpoint_consistent,
            camera_calibrated=payload.camera_calibrated,
            processed_at=_now_iso(),
            device_health=device_health,
        )

        transition = self._engine.consume_transition()
        if transition is not None:
            import asyncio
            from dataclasses import asdict

            incident = {**asdict(processed_state), "state": transition}
            asyncio.ensure_future(schedule_incident_report(incident))

        return processed_state
