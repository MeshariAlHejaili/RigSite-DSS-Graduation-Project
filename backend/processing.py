from __future__ import annotations

import datetime

import anomaly_engine
from config import interpolate_expected_flow


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


def process_payload(raw: dict, pete: dict) -> dict:
    state = dict(raw)
    state.setdefault(
        "device_health",
        {"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": True},
    )
    state.update(
        pressure_diff=None,
        expected_flow=None,
        flow_deviation_pct=None,
        state=None,
        decision_confidence=None,
        sensor_status=None,
        processed_at=None,
    )

    required_fields = ("pressure1", "pressure2", "flow", "gate_angle", "timestamp")
    faults: set[str] = {field for field in required_fields if raw.get(field) is None}

    if raw.get("pressure1") is not None and not (0.0 <= raw["pressure1"] <= 20.0):
        faults.add("pressure1")
    if raw.get("pressure2") is not None and not (0.0 <= raw["pressure2"] <= 20.0):
        faults.add("pressure2")
    if raw.get("flow") is not None and not (0.0 <= raw["flow"] <= 30.0):
        faults.add("flow")
    if raw.get("gate_angle") is not None and not (0.0 <= raw["gate_angle"] <= 90.0):
        faults.add("gate_angle")
    if raw.get("angle_confidence") is not None and not (0.0 <= raw["angle_confidence"] <= 1.0):
        faults.add("angle_confidence")

    if faults:
        state["sensor_status"] = _fault_from_validation(faults, state["device_health"])
        state["state"] = "SENSOR_FAULT"
        state["pressure_diff"] = 0.0
        state["expected_flow"] = 0.0
        state["flow_deviation_pct"] = 0.0
        state["decision_confidence"] = 0.0
        state["processed_at"] = _now_iso()
        return state

    state["sensor_status"] = _sensor_fault_from_health(state["device_health"])
    state["pressure_diff"] = round(raw["pressure1"] - raw["pressure2"], 4)
    state["expected_flow"] = interpolate_expected_flow(
        raw["gate_angle"],
        flow_baseline=float(pete["flow_baseline"]),
    )

    if state["expected_flow"] == 0:
        state["flow_deviation_pct"] = 0.0
    else:
        state["flow_deviation_pct"] = round(
            ((raw["flow"] - state["expected_flow"]) / state["expected_flow"]) * 100.0,
            4,
        )

    state["state"] = anomaly_engine.evaluate(
        state["flow_deviation_pct"],
        float(pete["anomaly_threshold"]),
        int(pete["anomaly_window"]),
    )

    raw_conf = min(
        float(raw.get("angle_confidence", 0.0)),
        1.0 - abs(state["flow_deviation_pct"]) / 100.0,
    )
    state["decision_confidence"] = round(max(0.0, min(1.0, raw_conf)), 4)
    state["processed_at"] = _now_iso()
    anomaly_engine.schedule_transition_actions(state)
    return state


if __name__ == "__main__":
    import time

    from anomaly_engine import AnomalyEngine, reset_active_engine, set_active_engine

    def run_test(label, raws, pete, expect):
        engine = AnomalyEngine()
        token = set_active_engine(engine)
        try:
            result = None
            for raw_payload in raws:
                result = process_payload(raw_payload, pete)
            assert result["state"] == expect, f"FAIL {label}: got {result['state']}"
            print(f"PASS {label}")
        finally:
            reset_active_engine(token)

    pete = {"flow_baseline": 10.0, "anomaly_threshold": 0.15, "anomaly_window": 2}
    ts = time.time()

    normal_raw = {
        "timestamp": ts,
        "pressure1": 5.0,
        "pressure2": 4.0,
        "flow": 6.5,
        "gate_angle": 60.0,
        "angle_confidence": 0.9,
        "device_health": {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        },
    }
    run_test("normal -> NORMAL", [normal_raw] * 3, pete, "NORMAL")

    kick_raw = {
        "timestamp": ts,
        "pressure1": 5.5,
        "pressure2": 4.0,
        "flow": 8.5,
        "gate_angle": 60.0,
        "angle_confidence": 0.88,
        "device_health": {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        },
    }
    run_test("kick x2 -> KICK_RISK", [kick_raw] * 2, pete, "KICK_RISK")

    bad_raw = {
        "timestamp": ts,
        "pressure1": 5.0,
        "pressure2": 4.0,
        "flow": None,
        "gate_angle": 60.0,
        "angle_confidence": 0.9,
        "device_health": {
            "pressure_sensor_ok": True,
            "flow_sensor_ok": True,
            "camera_ok": True,
        },
    }
    engine = AnomalyEngine()
    token = set_active_engine(engine)
    try:
        result = process_payload(bad_raw, pete)
        assert result["state"] == "SENSOR_FAULT", f"FAIL: got {result['state']}"
        print("PASS missing flow -> SENSOR_FAULT")
    finally:
        reset_active_engine(token)
