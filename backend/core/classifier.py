"""Single-sample deviation classifier used by the anomaly engine."""
from __future__ import annotations


def classify_deviation(deviation_pct: float, threshold: float) -> str:
    limit = threshold * 100.0
    if deviation_pct > limit:
        return "KICK_RISK"
    if deviation_pct < -limit:
        return "LOSS_RISK"
    return "NORMAL"
