"""Configuration: env vars, runtime settings, and engineering constants."""
from __future__ import annotations

import bisect
import os

from dotenv import load_dotenv

# .env lives at the project root.
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
CUTTINGS_DENSITY = float(os.getenv("CUTTINGS_DENSITY", "21.0"))
CUTTINGS_VOLUME_FRACTION = float(os.getenv("CUTTINGS_VOLUME_FRACTION", "0.0"))
SUSPENSION_FACTOR = float(os.getenv("SUSPENSION_FACTOR", "1.0"))
DISPLAY_MUD_WEIGHT = os.getenv("DISPLAY_MUD_WEIGHT", "normal")
INGEST_SAMPLE_RATE_HZ = float(os.getenv("INGEST_SAMPLE_RATE_HZ", "1.0"))

VISCOSITY_PIPE_DIAMETER_M = float(os.getenv("VISCOSITY_PIPE_DIAMETER_M", "0.1"))
VISCOSITY_SENSOR_SPACING_M = float(os.getenv("VISCOSITY_SENSOR_SPACING_M", "1.0"))
VISCOSITY_FLUID_VELOCITY_M_S = float(os.getenv("VISCOSITY_FLUID_VELOCITY_M_S", "1.0"))

PETE_KEYS = (
    "flow_baseline",
    "anomaly_threshold",
    "anomaly_window",
    "cuttings_density",
    "cuttings_volume_fraction",
    "suspension_factor",
)
SYSTEM_SETTING_KEYS = ("display_mud_weight",)
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


def _coerce_detection_mode(value: str) -> str:
    if value == "angle_density":
        return "angle_mud_weight"
    if value not in ("angle_only", "angle_mud_weight"):
        raise ValueError(f"Invalid detection_mode: {value!r}")
    return value


def _coerce_display_mud_weight(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in ("normal", "cuttings"):
        raise ValueError(f"Invalid display_mud_weight: {value!r}")
    return normalized


def coerce_pete_value(key: str, value: float | int | str) -> float | int:
    numeric = float(value)
    if key == "anomaly_window":
        return max(1, int(numeric))
    if key == "cuttings_volume_fraction":
        return min(max(numeric, 0.0), 1.0)
    if key == "suspension_factor":
        return max(numeric, 0.0)
    return numeric


PETE: dict[str, float | int] = {
    "flow_baseline": coerce_pete_value("flow_baseline", FLOW_BASELINE),
    "anomaly_threshold": coerce_pete_value("anomaly_threshold", ANOMALY_THRESHOLD),
    "anomaly_window": coerce_pete_value("anomaly_window", ANOMALY_WINDOW),
    "cuttings_density": coerce_pete_value("cuttings_density", CUTTINGS_DENSITY),
    "cuttings_volume_fraction": coerce_pete_value("cuttings_volume_fraction", CUTTINGS_VOLUME_FRACTION),
    "suspension_factor": coerce_pete_value("suspension_factor", SUSPENSION_FACTOR),
}
SYSTEM_SETTINGS: dict[str, str] = {
    "display_mud_weight": _coerce_display_mud_weight(DISPLAY_MUD_WEIGHT),
}


def set_pete_constant(key: str, value: float | int | str) -> None:
    PETE[key] = coerce_pete_value(key, value)


def set_system_setting(key: str, value: str) -> None:
    if key != "display_mud_weight":
        raise ValueError(f"Unknown system setting: {key!r}")
    SYSTEM_SETTINGS[key] = _coerce_display_mud_weight(value)


def get_pete_constants() -> dict[str, float | int]:
    return {key: PETE[key] for key in PETE_KEYS}


def get_system_settings() -> dict[str, str]:
    return {key: SYSTEM_SETTINGS[key] for key in SYSTEM_SETTING_KEYS}


def get_runtime_config() -> dict[str, float | int | str]:
    return {**get_pete_constants(), **get_system_settings()}


def get_viscosity_constants() -> dict[str, float]:
    return {
        "pipe_diameter_m": VISCOSITY_PIPE_DIAMETER_M,
        "sensor_spacing_m": VISCOSITY_SENSOR_SPACING_M,
        "fluid_velocity_m_s": VISCOSITY_FLUID_VELOCITY_M_S,
    }


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


DETECTION_MODE = _coerce_detection_mode(os.getenv("DETECTION_MODE", "angle_only"))
DELTA_H_FT = float(os.getenv("DELTA_H_FT", os.getenv("DELTA_H", "1.0")))

DETECTION_SETTINGS: dict[str, float | int | str | None] = {
    "detection_mode": DETECTION_MODE,
    "delta_h_ft": max(0.001, DELTA_H_FT),
    "baseline_angle": None,
    "baseline_mud_weight": None,
    "baseline_version": 0,
}


def get_detection_settings() -> dict[str, float | int | str | None]:
    return dict(DETECTION_SETTINGS)


def set_detection_setting(key: str, value: object) -> None:
    if key == "detection_mode":
        DETECTION_SETTINGS["detection_mode"] = _coerce_detection_mode(str(value))
        return
    if key in {"delta_h_ft", "delta_h"}:
        DETECTION_SETTINGS["delta_h_ft"] = max(0.001, float(value))  # type: ignore[arg-type]
        return
    raise ValueError(f"Unknown detection setting: {key!r}")


def set_detection_baseline(
    baseline_angle: float,
    baseline_mud_weight: float | None = None,
) -> None:
    """Fix the detection baseline and increment baseline_version."""

    DETECTION_SETTINGS["baseline_angle"] = round(float(baseline_angle), 4)
    DETECTION_SETTINGS["baseline_mud_weight"] = (
        round(float(baseline_mud_weight), 4) if baseline_mud_weight is not None else None
    )
    DETECTION_SETTINGS["baseline_version"] = int(DETECTION_SETTINGS["baseline_version"]) + 1


def theoretical_alarm_latency_seconds(
    sample_rate_hz: float | None = None,
    anomaly_window: int | None = None,
) -> float:
    rate = INGEST_SAMPLE_RATE_HZ if sample_rate_hz is None else max(float(sample_rate_hz), 1e-9)
    window = int(PETE["anomaly_window"] if anomaly_window is None else anomaly_window)
    return round(window / rate, 4)
