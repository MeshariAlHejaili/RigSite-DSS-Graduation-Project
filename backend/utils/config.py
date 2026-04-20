"""Configuration: env vars, constants, and the in-memory PETE cache."""
from __future__ import annotations

import bisect
import os

from dotenv import load_dotenv

# .env lives at the project root — two levels above this file (backend/utils/ → backend/ → project root)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "riglab")
POSTGRES_USER = os.getenv("POSTGRES_USER", "riglab_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "riglab_pass")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

FLOW_BASELINE = float(os.getenv("FLOW_BASELINE", "10.0"))
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.15"))
ANOMALY_WINDOW = int(os.getenv("ANOMALY_WINDOW", "2"))
INGEST_SAMPLE_RATE_HZ = float(os.getenv("INGEST_SAMPLE_RATE_HZ", "1.0"))

PETE_KEYS = ("flow_baseline", "anomaly_threshold", "anomaly_window")
FLOW_CALIBRATION_REFERENCE_BASELINE = 10.0
DEFAULT_FLOW_CALIBRATION_POINTS = (
    (0.0, 0.0),
    (15.0, 1.6667),
    (30.0, 3.3333),
    (45.0, 5.0),
    (60.0, 6.6667),
    (75.0, 8.3333),
    (90.0, 10.0),
)


def _parse_calibration_points(raw_points: str | None) -> tuple[tuple[float, float], ...]:
    if not raw_points:
        return DEFAULT_FLOW_CALIBRATION_POINTS

    points: list[tuple[float, float]] = []
    for raw_point in raw_points.split(","):
        angle_text, flow_text = raw_point.split(":")
        points.append((float(angle_text.strip()), float(flow_text.strip())))
    points.sort(key=lambda point: point[0])
    return tuple(points)


FLOW_CALIBRATION_POINTS = _parse_calibration_points(os.getenv("FLOW_CALIBRATION_POINTS"))
FLOW_CALIBRATION_ANGLES = tuple(point[0] for point in FLOW_CALIBRATION_POINTS)


def coerce_pete_value(key: str, value: float | int | str) -> float | int:
    numeric = float(value)
    if key == "anomaly_window":
        return max(1, int(numeric))
    return numeric


PETE: dict[str, float | int] = {
    "flow_baseline": coerce_pete_value("flow_baseline", FLOW_BASELINE),
    "anomaly_threshold": coerce_pete_value("anomaly_threshold", ANOMALY_THRESHOLD),
    "anomaly_window": coerce_pete_value("anomaly_window", ANOMALY_WINDOW),
}


def set_pete_constant(key: str, value: float | int | str) -> None:
    PETE[key] = coerce_pete_value(key, value)


def get_pete_constants() -> dict[str, float | int]:
    return {key: PETE[key] for key in PETE_KEYS}


def _scaled_calibration_points(flow_baseline: float | None = None) -> tuple[tuple[float, float], ...]:
    baseline = FLOW_BASELINE if flow_baseline is None else float(flow_baseline)
    scale = baseline / FLOW_CALIBRATION_REFERENCE_BASELINE
    return tuple((angle, flow * scale) for angle, flow in FLOW_CALIBRATION_POINTS)


def interpolate_expected_flow(gate_angle: float, flow_baseline: float | None = None) -> float:
    angle = max(0.0, min(90.0, float(gate_angle)))
    points = _scaled_calibration_points(flow_baseline)
    if angle <= points[0][0]:
        return round(points[0][1], 4)
    if angle >= points[-1][0]:
        return round(points[-1][1], 4)

    insert_at = bisect.bisect_left(FLOW_CALIBRATION_ANGLES, angle)
    lower_angle, lower_flow = points[insert_at - 1]
    upper_angle, upper_flow = points[insert_at]
    span = upper_angle - lower_angle
    if span <= 0:
        return round(lower_flow, 4)

    ratio = (angle - lower_angle) / span
    interpolated = lower_flow + (upper_flow - lower_flow) * ratio
    return round(interpolated, 4)


DETECTION_MODE = os.getenv("DETECTION_MODE", "angle_only")
DELTA_H = float(os.getenv("DELTA_H", "1.0"))

DETECTION_SETTINGS: dict = {
    "detection_mode": DETECTION_MODE,
    "delta_h": DELTA_H,
    # Baseline — None until the engineer sets it from the UI
    "baseline_angle": None,
    "baseline_density": None,
    "baseline_version": 0,  # incremented each time the baseline is changed
}


def get_detection_settings() -> dict:
    return dict(DETECTION_SETTINGS)


def set_detection_setting(key: str, value: object) -> None:
    if key == "detection_mode":
        if value not in ("angle_only", "angle_density"):
            raise ValueError(f"Invalid detection_mode: {value!r}")
        DETECTION_SETTINGS["detection_mode"] = value
    elif key == "delta_h":
        DETECTION_SETTINGS["delta_h"] = max(0.001, float(value))  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown detection setting: {key!r}")


def set_detection_baseline(
    baseline_angle: float, baseline_density: float | None = None
) -> None:
    """Fix the detection baseline. Increments baseline_version so all engines resync."""
    DETECTION_SETTINGS["baseline_angle"] = round(float(baseline_angle), 4)
    DETECTION_SETTINGS["baseline_density"] = (
        round(float(baseline_density), 4) if baseline_density is not None else None
    )
    DETECTION_SETTINGS["baseline_version"] = int(DETECTION_SETTINGS["baseline_version"]) + 1


def theoretical_alarm_latency_seconds(
    sample_rate_hz: float | None = None,
    anomaly_window: int | None = None,
) -> float:
    rate = INGEST_SAMPLE_RATE_HZ if sample_rate_hz is None else max(float(sample_rate_hz), 1e-9)
    window = int(PETE["anomaly_window"] if anomaly_window is None else anomaly_window)
    return round(window / rate, 4)
