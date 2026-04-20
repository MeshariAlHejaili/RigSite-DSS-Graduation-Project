"""Angle-based kick/loss detection engine with two selectable modes.

Baseline is FIXED — set manually by the engineer via the UI.
Detection does not start until a baseline is set.
Exiting an alarm requires CLEAR_REQUIRED consecutive in-range points.
"""
from __future__ import annotations

import asyncio
import datetime
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Awaitable, Callable

from reports.generator import incident_pdf

ANGLE_THRESHOLD_DEG = 5.0
DENSITY_THRESHOLD_PCT = 0.10
CONSECUTIVE_REQUIRED = 3   # consecutive trigger points to enter alarm
CLEAR_REQUIRED = 3         # consecutive in-range points to exit alarm

TransitionHandler = Callable[[dict], Awaitable[None] | None]

_ACTIVE_DETECTION_ENGINE: ContextVar["DetectionEngine | None"] = ContextVar(
    "active_detection_engine", default=None
)
_INCIDENT_OUTPUT_DIR = Path(__file__).resolve().parent / "reports" / "generated"


class DetectionEngine:
    def __init__(self) -> None:
        self._mode = "angle_only"
        # Baseline — None until engineer sets it via UI
        self._baseline_angle: float | None = None
        self._baseline_density: float | None = None
        # Tracks the config baseline version to detect when engineer updates it
        self._baseline_version: int = -1
        # Streak counters
        self._kick_streak = 0
        self._loss_streak = 0
        self._clear_streak = 0
        self._last_state = "NORMAL"
        self._pending_transition: str | None = None
        # Last seen values (for display)
        self._last_angle: float | None = None
        self._last_density: float | None = None

    def _reset_streaks(self) -> None:
        self._kick_streak = 0
        self._loss_streak = 0
        self._clear_streak = 0
        self._last_state = "NORMAL"
        self._pending_transition = None

    def sync_baseline_from_config(self, detection_settings: dict) -> None:
        """Apply baseline from config if the engineer has updated it."""
        config_version = int(detection_settings.get("baseline_version", 0))
        if config_version == self._baseline_version:
            return
        # Baseline was updated — apply it and reset streaks
        self._baseline_version = config_version
        self._baseline_angle = detection_settings.get("baseline_angle")
        self._baseline_density = detection_settings.get("baseline_density")
        self._reset_streaks()

    def evaluate(self, angle: float | None, density: float | None, mode: str) -> str:
        if mode != self._mode:
            self._mode = mode
            self._reset_streaks()

        if angle is None:
            return "NORMAL"

        self._last_angle = angle
        self._last_density = density

        # No baseline set yet — hold in NORMAL until engineer sets one
        if self._baseline_angle is None:
            return "NORMAL"

        kick_cond, loss_cond = self._check_conditions(angle, density, mode)

        if kick_cond:
            self._kick_streak += 1
            self._loss_streak = 0
            self._clear_streak = 0
        elif loss_cond:
            self._loss_streak += 1
            self._kick_streak = 0
            self._clear_streak = 0
        else:
            self._clear_streak += 1
            self._kick_streak = 0
            self._loss_streak = 0

        # Determine next state
        if self._kick_streak >= CONSECUTIVE_REQUIRED:
            next_state = "KICK_RISK"
        elif self._loss_streak >= CONSECUTIVE_REQUIRED:
            next_state = "LOSS_RISK"
        elif self._last_state in ("KICK_RISK", "LOSS_RISK") and self._clear_streak >= CLEAR_REQUIRED:
            # Alarm clears only after CLEAR_REQUIRED consecutive in-range points
            next_state = "NORMAL"
        elif self._last_state in ("KICK_RISK", "LOSS_RISK"):
            # Stay in alarm until cleared
            next_state = self._last_state
        else:
            next_state = "NORMAL"

        if self._last_state == "NORMAL" and next_state in {"KICK_RISK", "LOSS_RISK"}:
            self._pending_transition = next_state

        self._last_state = next_state
        return next_state

    def _check_conditions(
        self, angle: float, density: float | None, mode: str
    ) -> tuple[bool, bool]:
        base = self._baseline_angle

        angle_kick = angle > base + ANGLE_THRESHOLD_DEG
        angle_loss = angle < base - ANGLE_THRESHOLD_DEG

        if mode == "angle_density" and density is not None and self._baseline_density is not None:
            density_kick = density > self._baseline_density * (1.0 + DENSITY_THRESHOLD_PCT)
            density_loss = density < self._baseline_density * (1.0 - DENSITY_THRESHOLD_PCT)
            return (angle_kick or density_kick), (angle_loss or density_loss)

        return angle_kick, angle_loss

    def get_display_state(self) -> dict:
        angle_deviation = None
        density_deviation_pct = None

        if self._baseline_angle is not None and self._last_angle is not None:
            angle_deviation = round(self._last_angle - self._baseline_angle, 4)

        if (
            self._baseline_density is not None
            and self._last_density is not None
            and self._baseline_density != 0
        ):
            density_deviation_pct = round(
                (self._last_density - self._baseline_density) / self._baseline_density * 100.0, 4
            )

        return {
            "angle_deviation": angle_deviation,
            "density_deviation_pct": density_deviation_pct,
            "baseline_angle": round(self._baseline_angle, 4) if self._baseline_angle is not None else None,
        }

    def consume_transition(self) -> str | None:
        transition = self._pending_transition
        self._pending_transition = None
        return transition


# ── Incident report helpers (unchanged from previous version) ──────

def _row_for_incident_report(state: dict) -> dict:
    record = dict(state)
    timestamp = record.get("timestamp")
    if isinstance(timestamp, (int, float)):
        record["timestamp"] = (
            datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    record.setdefault(
        "processed_at",
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    return record


def _incident_snapshot_path(state: dict) -> Path:
    timestamp = state.get("processed_at")
    safe_ts = str(timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()).replace(":", "-")
    return _INCIDENT_OUTPUT_DIR / f"incident_{state['state'].lower()}_{safe_ts}.pdf"


def _write_incident_snapshot(state: dict) -> Path:
    _INCIDENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _incident_snapshot_path(state)
    path.write_bytes(incident_pdf([_row_for_incident_report(state)]))
    return path


async def _default_transition_handler(state: dict) -> None:
    await asyncio.to_thread(_write_incident_snapshot, state)


def schedule_transition_actions(state: dict) -> None:
    engine = _ACTIVE_DETECTION_ENGINE.get()
    if engine is None:
        return

    transition_state = engine.consume_transition()
    if transition_state is None:
        return

    incident_state = dict(state)
    incident_state["state"] = transition_state

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_default_transition_handler(incident_state))
    except RuntimeError:
        _write_incident_snapshot(incident_state)


# ── Context variable helpers ──────────────────────────────────────

def set_active_engine(engine: DetectionEngine) -> Token:
    return _ACTIVE_DETECTION_ENGINE.set(engine)


def reset_active_engine(token: Token) -> None:
    _ACTIVE_DETECTION_ENGINE.reset(token)


def get_active_engine() -> DetectionEngine | None:
    return _ACTIVE_DETECTION_ENGINE.get()


def sync_baseline(detection_settings: dict) -> None:
    engine = _ACTIVE_DETECTION_ENGINE.get()
    if engine is None:
        return
    engine.sync_baseline_from_config(detection_settings)


def evaluate(angle: float | None, density: float | None, mode: str) -> str:
    engine = _ACTIVE_DETECTION_ENGINE.get()
    if engine is None:
        engine = DetectionEngine()
    return engine.evaluate(angle, density, mode)


def get_display_state() -> dict:
    engine = _ACTIVE_DETECTION_ENGINE.get()
    if engine is None:
        return {"angle_deviation": None, "density_deviation_pct": None, "baseline_angle": None}
    return engine.get_display_state()
