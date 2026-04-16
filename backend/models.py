"""Dataclasses for raw payloads, processed state, and DB records."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeviceHealth:
    pressure_sensor_ok: bool
    flow_sensor_ok: bool
    camera_ok: bool


@dataclass
class RawPayload:
    """Raw inbound payload from Pi / mock generator (Section 5.1)."""
    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: Optional[float]
    angle_confidence: float
    device_health: dict


@dataclass
class ProcessedState:
    """Processed state broadcast to /ws/live and stored in DB (Section 5.2)."""
    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: Optional[float]
    angle_confidence: float
    device_health: dict
    pressure_diff: float
    expected_flow: float
    flow_deviation_pct: float
    state: str
    decision_confidence: float
    sensor_status: str
    processed_at: str
