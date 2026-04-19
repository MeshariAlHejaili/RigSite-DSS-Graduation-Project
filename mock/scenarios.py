from __future__ import annotations

import math
import random
import time

FLOW_BASELINE = 10.0


def _noise(amount: float) -> float:
    return random.uniform(-amount, amount)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _expected_flow(gate_angle: float) -> float:
    return FLOW_BASELINE * (gate_angle / 90.0)


def _base_payload(
    gate_angle: float | None,
    flow: float,
    pressure1: float,
    pressure2: float,
    device_health: dict,
) -> dict:
    return {
        "timestamp": time.time(),
        "pressure1": pressure1,
        "pressure2": pressure2,
        "flow": flow,
        "gate_angle": gate_angle,
        "device_health": device_health,
    }


def normal(sample_index: int) -> dict:
    gate_angle = _clamp(50.0 + 14.0 * math.sin(sample_index / 4.0) + _noise(1.5), 20.0, 82.0)
    expected_flow = _expected_flow(gate_angle)
    flow = expected_flow * (1.0 + _noise(0.08))
    pressure1 = 4.9 + 0.35 * math.sin(sample_index / 6.0) + _noise(0.08)
    pressure2 = pressure1 - (0.95 + _noise(0.08))
    return _base_payload(
        gate_angle=gate_angle,
        flow=flow,
        pressure1=pressure1,
        pressure2=pressure2,
        device_health={"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": True},
    )


def kick(sample_index: int) -> dict:
    gate_angle = _clamp(42.0 + 18.0 * math.sin(sample_index / 3.0) + _noise(1.2), 18.0, 78.0)
    expected_flow = _expected_flow(gate_angle)
    flow = expected_flow * (1.32 + _noise(0.03))
    pressure1 = 5.3 + 0.45 * math.sin(sample_index / 5.0) + _noise(0.08)
    pressure2 = pressure1 - (1.35 + _noise(0.08))
    return _base_payload(
        gate_angle=gate_angle,
        flow=flow,
        pressure1=pressure1,
        pressure2=pressure2,
        device_health={"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": True},
    )


def loss(sample_index: int) -> dict:
    gate_angle = _clamp(60.0 + 16.0 * math.sin(sample_index / 3.5) + _noise(1.2), 24.0, 86.0)
    expected_flow = _expected_flow(gate_angle)
    flow = expected_flow * (0.64 + _noise(0.03))
    pressure1 = 4.4 + 0.3 * math.sin(sample_index / 5.0) + _noise(0.08)
    pressure2 = pressure1 - (0.72 + _noise(0.08))
    return _base_payload(
        gate_angle=gate_angle,
        flow=flow,
        pressure1=pressure1,
        pressure2=pressure2,
        device_health={"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": True},
    )


def drift(sample_index: int) -> dict:
    gate_angle = _clamp(48.0 + 10.0 * math.sin(sample_index / 5.0) + _noise(1.0), 24.0, 76.0)
    expected_flow = _expected_flow(gate_angle)
    drift_factor = 1.0 + min(sample_index, 60) * 0.005
    flow = expected_flow * (drift_factor + _noise(0.02))
    pressure1 = 5.0 + 0.25 * math.sin(sample_index / 6.0) + _noise(0.08)
    pressure2 = pressure1 - (0.9 + _noise(0.08))
    return _base_payload(
        gate_angle=gate_angle,
        flow=flow,
        pressure1=pressure1,
        pressure2=pressure2,
        device_health={"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": True},
    )


def camera_fault(sample_index: int) -> dict:
    pressure1 = 5.0 + _noise(0.1)
    pressure2 = 4.0 + _noise(0.1)
    flow = 6.5 + _noise(0.3)
    return _base_payload(
        gate_angle=None,
        flow=flow,
        pressure1=pressure1,
        pressure2=pressure2,
        device_health={"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": False},
    )
