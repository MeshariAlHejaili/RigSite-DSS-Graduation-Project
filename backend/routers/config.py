from __future__ import annotations

from fastapi import APIRouter, HTTPException

from utils import config as cfg
from utils import database

router = APIRouter()

ALLOWED_PETE_KEYS = set(cfg.PETE_KEYS)


@router.get("/config")
async def get_config():
    return cfg.get_pete_constants()


@router.post("/config")
async def update_config(body: dict):
    invalid = set(body.keys()) - ALLOWED_PETE_KEYS
    if invalid:
        raise HTTPException(400, f"Unknown keys: {invalid}")

    pool = database.get_pool()
    async with pool.acquire() as conn:
        for key, value in body.items():
            await conn.execute(
                "UPDATE pete_constants SET value = $1, updated_at = NOW() WHERE key = $2",
                float(value),
                key,
            )
            cfg.set_pete_constant(key, value)

    return {"updated": list(body.keys()), "current": cfg.get_pete_constants()}


@router.get("/detection-config")
async def get_detection_config():
    return cfg.get_detection_settings()


@router.post("/detection-config")
async def update_detection_config(body: dict):
    allowed = {"detection_mode", "delta_h"}
    invalid = set(body.keys()) - allowed
    if invalid:
        raise HTTPException(400, f"Unknown keys: {invalid}")

    for key, value in body.items():
        try:
            cfg.set_detection_setting(key, value)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    return cfg.get_detection_settings()


@router.post("/detection-config/set-baseline")
async def set_baseline(body: dict):
    """Fix the detection baseline from the last N data points (calculated by the frontend).

    Body: { "baseline_angle": float, "baseline_density": float | null }
    Increments baseline_version so every active engine resyncs on next evaluation.
    """
    baseline_angle = body.get("baseline_angle")
    if baseline_angle is None:
        raise HTTPException(400, "baseline_angle is required")

    try:
        baseline_angle = float(baseline_angle)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "baseline_angle must be a number") from exc

    baseline_density = body.get("baseline_density")
    if baseline_density is not None:
        try:
            baseline_density = float(baseline_density)
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, "baseline_density must be a number or null") from exc

    cfg.set_detection_baseline(baseline_angle, baseline_density)
    return cfg.get_detection_settings()
