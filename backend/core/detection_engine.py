"""Angle-based kick/loss detection engine with optional mud-weight support."""
from __future__ import annotations

import asyncio
import datetime
from pathlib import Path

from reports.generator import incident_pdf

ANGLE_THRESHOLD_DEG = 5.0
MUD_WEIGHT_THRESHOLD_PCT = 0.10
CONSECUTIVE_REQUIRED = 3
CLEAR_REQUIRED = 3

_INCIDENT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "generated"


class DetectionEngine:
    def __init__(self) -> None:
        self._mode = "angle_only"
        self._baseline_angle: float | None = None
        self._baseline_mud_weight: float | None = None
        self._baseline_version: int = -1
        self._kick_streak = 0
        self._loss_streak = 0
        self._clear_streak = 0
        self._last_state = "NORMAL"
        self._pending_transition: str | None = None
        self._last_angle: float | None = None
        self._last_mud_weight: float | None = None

    def _reset_streaks(self) -> None:
        self._kick_streak = 0
        self._loss_streak = 0
        self._clear_streak = 0
        self._last_state = "NORMAL"
        self._pending_transition = None

    def sync_baseline_from_config(self, detection_settings: dict) -> None:
        """Apply baseline from config only when the engineer has updated it."""
        config_version = int(detection_settings.get("baseline_version", 0))
        if config_version == self._baseline_version:
            return
        self._baseline_version = config_version
        self._baseline_angle = detection_settings.get("baseline_angle")
        self._baseline_mud_weight = detection_settings.get("baseline_mud_weight")
        self._reset_streaks()

    def evaluate(self, angle: float | None, mud_weight: float | None, mode: str) -> str:
        if mode != self._mode:
            self._mode = mode
            self._reset_streaks()

        if angle is None:
            return "NORMAL"

        self._last_angle = angle
        self._last_mud_weight = mud_weight

        if self._baseline_angle is None:
            return "NORMAL"

        if mode == "angle_mud_weight" and self._baseline_mud_weight is None:
            # In angle+mud mode, alerts stay disabled until mud baseline is explicitly set.
            self._reset_streaks()
            return "NORMAL"

        if mode == "angle_mud_weight" and mud_weight is None:
            # A missing mud-weight point breaks streak continuity in combined mode.
            self._reset_streaks()
            return "NORMAL"

        kick_cond, loss_cond = self._check_conditions(angle, mud_weight, mode)

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

        if self._kick_streak >= CONSECUTIVE_REQUIRED:
            next_state = "KICK_RISK"
        elif self._loss_streak >= CONSECUTIVE_REQUIRED:
            next_state = "LOSS_RISK"
        elif self._last_state in ("KICK_RISK", "LOSS_RISK") and self._clear_streak >= CLEAR_REQUIRED:
            next_state = "NORMAL"
        elif self._last_state in ("KICK_RISK", "LOSS_RISK"):
            next_state = self._last_state
        else:
            next_state = "NORMAL"

        if self._last_state == "NORMAL" and next_state in {"KICK_RISK", "LOSS_RISK"}:
            self._pending_transition = next_state

        self._last_state = next_state
        return next_state

    def _check_conditions(
        self,
        angle: float,
        mud_weight: float | None,
        mode: str,
    ) -> tuple[bool, bool]:
        base_angle = self._baseline_angle
        angle_kick = angle > base_angle + ANGLE_THRESHOLD_DEG
        angle_loss = angle < base_angle - ANGLE_THRESHOLD_DEG

        if mode == "angle_mud_weight":
            if mud_weight is None or self._baseline_mud_weight is None:
                return False, False
            mud_weight_kick = mud_weight > self._baseline_mud_weight * (1.0 + MUD_WEIGHT_THRESHOLD_PCT)
            mud_weight_loss = mud_weight < self._baseline_mud_weight * (1.0 - MUD_WEIGHT_THRESHOLD_PCT)
            return (angle_kick or mud_weight_kick), (angle_loss or mud_weight_loss)

        return angle_kick, angle_loss

    def get_display_state(self) -> dict:
        angle_deviation = None
        mud_weight_deviation_pct = None

        if self._baseline_angle is not None and self._last_angle is not None:
            angle_deviation = round(self._last_angle - self._baseline_angle, 4)

        if (
            self._baseline_mud_weight is not None
            and self._last_mud_weight is not None
            and self._baseline_mud_weight != 0
        ):
            mud_weight_deviation_pct = round(
                (self._last_mud_weight - self._baseline_mud_weight) / self._baseline_mud_weight * 100.0,
                4,
            )

        return {
            "angle_deviation": angle_deviation,
            "mud_weight_deviation_pct": mud_weight_deviation_pct,
            "baseline_angle": round(self._baseline_angle, 4) if self._baseline_angle is not None else None,
            "baseline_mud_weight": (
                round(self._baseline_mud_weight, 4) if self._baseline_mud_weight is not None else None
            ),
        }

    def consume_transition(self) -> str | None:
        """Return and clear any pending NORMAL-to-alarm transition."""
        transition = self._pending_transition
        self._pending_transition = None
        return transition


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


def write_incident_snapshot(state: dict) -> Path:
    """Write an incident PDF and return its path."""
    _INCIDENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _incident_snapshot_path(state)
    path.write_bytes(incident_pdf([_row_for_incident_report(state)]))
    return path


async def schedule_incident_report(state: dict) -> None:
    """Fire-and-forget: generate an incident PDF without blocking the pipeline."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(asyncio.to_thread(write_incident_snapshot, state))
    except RuntimeError:
        write_incident_snapshot(state)
