"""Shared contracts for backend processing and API serialization."""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

DisplayMudWeight = Literal["normal", "cuttings"]
DetectionMode = Literal["angle_only", "angle_mud_weight"]
TelemetryState = Literal["NORMAL", "KICK_RISK", "LOSS_RISK", "SENSOR_FAULT"]


@dataclass(frozen=True)
class SensorPayload:
    """Raw sensor reading exactly as received from any source."""

    pressure1: float
    pressure2: float
    flow: float
    gate_angle: float | None
    timestamp: float
    angle_confidence: float = 1.0
    angle_mode: Literal["mounted", "handheld"] = "mounted"
    angle_warning: str | None = None
    viewpoint_consistent: bool | None = None
    camera_calibrated: bool = False
    device_health: dict = field(
        default_factory=lambda: {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        }
    )


@dataclass(frozen=True)
class ProcessedState:
    """Fully computed state record ready for persistence and broadcast."""

    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: float | None
    pressure_diff: float
    expected_flow: float
    flow_deviation_pct: float
    mud_weight: float | None
    normal_mud_weight: float | None
    mud_weight_with_cuttings: float | None
    viscosity: float | None
    display_mud_weight: DisplayMudWeight
    angle_deviation: float | None
    mud_weight_deviation_pct: float | None
    baseline_angle: float | None
    baseline_mud_weight: float | None
    state: TelemetryState
    decision_confidence: float
    sensor_status: str
    detection_mode: DetectionMode
    angle_mode: Literal["mounted", "handheld"] | None
    angle_warning: str | None
    viewpoint_consistent: bool | None
    camera_calibrated: bool | None
    processed_at: str
    device_health: dict


class DeviceHealthModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pressure_sensor_ok: bool
    flow_sensor_ok: bool
    camera_ok: bool


class TelemetryRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: float | None
    pressure_diff: float
    expected_flow: float
    flow_deviation_pct: float
    mud_weight: float | None
    normal_mud_weight: float | None
    mud_weight_with_cuttings: float | None
    viscosity: float | None
    display_mud_weight: DisplayMudWeight
    angle_deviation: float | None
    mud_weight_deviation_pct: float | None
    baseline_angle: float | None
    baseline_mud_weight: float | None
    state: TelemetryState
    decision_confidence: float
    sensor_status: str
    detection_mode: DetectionMode
    angle_mode: Literal["mounted", "handheld"] | None = None
    angle_warning: str | None = None
    viewpoint_consistent: bool | None = None
    camera_calibrated: bool | None = None
    processed_at: str
    device_health: DeviceHealthModel


class TelemetryCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    records: list[TelemetryRecordResponse]


class SessionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    started_at: str
    ended_at: str | None
    record_count: int
    note: str | None = None


class SessionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: list[SessionSummaryResponse]


class RuntimeConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_baseline: float
    anomaly_threshold: float
    anomaly_window: int
    cuttings_density: float
    cuttings_volume_fraction: float
    suspension_factor: float
    display_mud_weight: DisplayMudWeight


class RuntimeConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_baseline: float | None = None
    anomaly_threshold: float | None = None
    anomaly_window: int | None = None
    cuttings_density: float | None = None
    cuttings_volume_fraction: float | None = None
    suspension_factor: float | None = None
    display_mud_weight: DisplayMudWeight | None = None


class DetectionConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detection_mode: DetectionMode
    delta_h_ft: float
    baseline_angle: float | None
    baseline_mud_weight: float | None
    baseline_version: int


class DetectionConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    detection_mode: str | None = None
    delta_h_ft: float | None = Field(
        default=None,
        validation_alias=AliasChoices("delta_h_ft", "delta_h"),
    )


class DetectionBaselineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    baseline_angle: float
    baseline_mud_weight: float | None = Field(
        default=None,
        validation_alias=AliasChoices("baseline_mud_weight", "baseline_density"),
    )


def _to_iso8601(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    raise TypeError(f"Unsupported timestamp value: {value!r}")


def processed_state_to_payload(state: ProcessedState) -> dict[str, Any]:
    payload = asdict(state)
    payload["timestamp"] = _to_iso8601(state.timestamp)
    return TelemetryRecordResponse.model_validate(payload).model_dump(mode="json")


def storage_record_to_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record)

    if "flow_deviation" in payload and "flow_deviation_pct" not in payload:
        payload["flow_deviation_pct"] = payload.pop("flow_deviation")
    if "decision_conf" in payload and "decision_confidence" not in payload:
        payload["decision_confidence"] = payload.pop("decision_conf")
    if "density" in payload and "mud_weight" not in payload:
        payload["mud_weight"] = payload.pop("density")
    if "density_deviation_pct" in payload and "mud_weight_deviation_pct" not in payload:
        payload["mud_weight_deviation_pct"] = payload.pop("density_deviation_pct")
    if "baseline_density" in payload and "baseline_mud_weight" not in payload:
        payload["baseline_mud_weight"] = payload.pop("baseline_density")

    if payload.get("timestamp") is not None:
        payload["timestamp"] = _to_iso8601(payload["timestamp"])
    if payload.get("processed_at") is not None:
        payload["processed_at"] = _to_iso8601(payload["processed_at"])
    elif payload.get("timestamp") is not None:
        payload["processed_at"] = payload["timestamp"]

    device_health = payload.get("device_health")
    if isinstance(device_health, str):
        payload["device_health"] = json.loads(device_health)

    payload.pop("id", None)
    if payload.get("display_mud_weight") is None:
        payload["display_mud_weight"] = "normal"
    payload.setdefault("angle_mode", None)
    payload.setdefault("angle_warning", None)
    payload.setdefault("viewpoint_consistent", None)
    payload.setdefault("camera_calibrated", None)

    if payload.get("mud_weight") is None:
        display_choice = payload["display_mud_weight"]
        payload["mud_weight"] = (
            payload.get("mud_weight_with_cuttings")
            if display_choice == "cuttings" and payload.get("mud_weight_with_cuttings") is not None
            else payload.get("normal_mud_weight")
        )

    # Ignore legacy/extra DB columns to keep history endpoints backward-compatible.
    allowed_fields = set(TelemetryRecordResponse.model_fields.keys())
    payload = {key: value for key, value in payload.items() if key in allowed_fields}

    return TelemetryRecordResponse.model_validate(payload).model_dump(mode="json")
