"""Dataclasses for raw payloads, processed state, and DB-shaped records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class DeviceHealth:
    pressure_sensor_ok: bool
    flow_sensor_ok: bool
    camera_ok: bool


@dataclass
class RawPayload:
    """Raw inbound payload from Pi / mock generator."""

    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: Optional[float]
    device_health: dict


@dataclass
class ProcessedState:
    """Processed state stored in DB and broadcast over the live channel."""

    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: Optional[float]
    device_health: dict
    pressure_diff: float
    expected_flow: float
    flow_deviation_pct: float
    mud_weight: Optional[float]
    normal_mud_weight: Optional[float]
    mud_weight_with_cuttings: Optional[float]
    viscosity: Optional[float]
    display_mud_weight: Literal["normal", "cuttings"]
    angle_deviation: Optional[float]
    mud_weight_deviation_pct: Optional[float]
    baseline_angle: Optional[float]
    baseline_mud_weight: Optional[float]
    state: str
    decision_confidence: float
    sensor_status: str
    detection_mode: Literal["angle_only", "angle_mud_weight"]
    processed_at: str
