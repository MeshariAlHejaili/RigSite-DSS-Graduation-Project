"""Immutable data-transfer types shared across all layers.

These are the only types that cross layer boundaries:
  SensorPayload  — ingestion layer → pipeline
  ProcessedState — pipeline → event bus → subscribers
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class SensorPayload:
    """Raw sensor reading exactly as received from any source.

    Field names deliberately match the wire format so data_sources can
    build instances without a translation table.
    """
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: float | None
    timestamp: float
    angle_confidence: float = 1.0
    device_health: dict = field(
        default_factory=lambda: {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        }
    )


@dataclass(frozen=True)
class ProcessedState:
    """Fully computed state record ready for persistence and broadcast.

    Every field maps 1-to-1 with a column in the telemetry table or a
    display field consumed by the dashboard.
    """
    timestamp: float
    pressure1: float
    pressure2: float
    flow: float
    gate_angle: float | None
    pressure_diff: float
    expected_flow: float
    flow_deviation_pct: float
    density: float | None
    angle_deviation: float | None
    density_deviation_pct: float | None
    baseline_angle: float | None
    state: Literal["NORMAL", "KICK_RISK", "LOSS_RISK", "SENSOR_FAULT"]
    decision_confidence: float
    sensor_status: str
    detection_mode: str
    processed_at: str
    device_health: dict
