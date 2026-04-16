from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "mock"))

import config  # noqa: E402
from anomaly_engine import AnomalyEngine, reset_active_engine, set_active_engine  # noqa: E402
from processing import process_payload  # noqa: E402
from scenarios import kick, loss, normal  # noqa: E402


def _build_payloads() -> list[tuple[str, dict]]:
    payloads: list[tuple[str, dict]] = []
    for index in range(40):
        payloads.append(("normal", normal(index)))
    for index in range(30):
        payloads.append(("kick", kick(index)))
    for index in range(30):
        payloads.append(("loss", loss(index)))
    return payloads


def _format_ms(value: float) -> str:
    return f"{value:.6f} ms"


def _alarm_latency_seconds(states: list[str], scenario_name: str, sample_rate_hz: float) -> float | None:
    target_state = "KICK_RISK" if scenario_name == "kick" else "LOSS_RISK"
    first_breach_index = next((index for index, _ in enumerate(states)), None)
    if first_breach_index is None:
        return None

    transition_index = next(
        (index for index, state in enumerate(states) if state == target_state),
        None,
    )
    if transition_index is None:
        return None

    samples_to_alarm = transition_index - first_breach_index + 1
    return round(samples_to_alarm / sample_rate_hz, 4)


def main() -> None:
    sample_rate_hz = config.INGEST_SAMPLE_RATE_HZ
    pete = config.get_pete_constants()
    payloads = _build_payloads()
    engine = AnomalyEngine()
    ingest_to_process_ms: list[float] = []
    classification_ms: list[float] = []
    kick_states: list[str] = []
    loss_states: list[str] = []

    token = set_active_engine(engine)
    try:
        for scenario_name, payload in payloads:
            payload["timestamp"] = time.time()
            started_at = time.time()
            state = process_payload(payload, pete)
            finished_at = time.time()

            ingest_to_process_ms.append((finished_at - started_at) * 1000.0)
            classification_ms.append(engine.last_evaluation_duration_ms)

            if scenario_name == "kick":
                kick_states.append(state["state"])
            elif scenario_name == "loss":
                loss_states.append(state["state"])
    finally:
        reset_active_engine(token)

    max_ingest_ms = max(ingest_to_process_ms)
    avg_ingest_ms = statistics.mean(ingest_to_process_ms)
    max_classification_ms = max(classification_ms)
    avg_classification_ms = statistics.mean(classification_ms)
    kick_alarm_latency_s = _alarm_latency_seconds(kick_states, "kick", sample_rate_hz)
    loss_alarm_latency_s = _alarm_latency_seconds(loss_states, "loss", sample_rate_hz)
    theoretical_alarm_s = config.theoretical_alarm_latency_seconds(
        sample_rate_hz=sample_rate_hz,
        anomaly_window=int(pete["anomaly_window"]),
    )

    dashboard_latency_ok = max_ingest_ms < 1000.0
    alarm_latency_ok = theoretical_alarm_s <= 2.0

    print("=" * 72)
    print("RigLab-AI Benchmark")
    print("=" * 72)
    print(f"Payloads processed        : {len(payloads)}")
    print(f"Configured sample rate    : {sample_rate_hz:.2f} Hz")
    print(f"Configured anomaly window : {int(pete['anomaly_window'])} samples")
    print(f"Calibration points        : {len(config.FLOW_CALIBRATION_POINTS)}")
    print("-" * 72)
    print(f"Average ingest->process   : {_format_ms(avg_ingest_ms)}")
    print(f"Max ingest->process       : {_format_ms(max_ingest_ms)}")
    print(f"Average classification    : {_format_ms(avg_classification_ms)}")
    print(f"Max classification        : {_format_ms(max_classification_ms)}")
    if max_classification_ms == 0.0:
        print("Classification timer note : below time.time() resolution on this host")
    print("-" * 72)
    print(f"Kick alarm latency        : {kick_alarm_latency_s:.4f} s")
    print(f"Loss alarm latency        : {loss_alarm_latency_s:.4f} s")
    print(f"Theoretical max alarm     : {theoretical_alarm_s:.4f} s")
    print("-" * 72)
    print(
        "Dashboard latency check   : "
        + ("PASS (< 1.0 s software path)" if dashboard_latency_ok else "FAIL")
    )
    print(
        "Alarm latency check       : "
        + ("PASS (window/sample rate <= 2.0 s)" if alarm_latency_ok else "FAIL")
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
