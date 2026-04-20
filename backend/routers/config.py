from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.schemas import (
    DetectionBaselineRequest,
    DetectionConfigResponse,
    DetectionConfigUpdateRequest,
    RuntimeConfigResponse,
    RuntimeConfigUpdateRequest,
)
from utils import config as cfg
from utils import database

router = APIRouter()


@router.get("/config", response_model=RuntimeConfigResponse)
async def get_config():
    return cfg.get_runtime_config()


@router.post("/config", response_model=RuntimeConfigResponse)
async def update_config(body: RuntimeConfigUpdateRequest):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "provide at least one config field")

    pool = database.get_pool()
    async with pool.acquire() as conn:
        for key, value in updates.items():
            if key in cfg.PETE_KEYS:
                await conn.execute(
                    """
                    INSERT INTO pete_constants (key, value, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    key,
                    float(value),
                )
                cfg.set_pete_constant(key, value)
            elif key in cfg.SYSTEM_SETTING_KEYS:
                await conn.execute(
                    """
                    INSERT INTO system_settings (key, value, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    key,
                    str(value),
                )
                cfg.set_system_setting(key, str(value))
            else:
                raise HTTPException(400, f"Unknown key: {key}")

    return cfg.get_runtime_config()


@router.get("/detection-config", response_model=DetectionConfigResponse)
async def get_detection_config():
    return cfg.get_detection_settings()


@router.post("/detection-config", response_model=DetectionConfigResponse)
async def update_detection_config(body: DetectionConfigUpdateRequest):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "provide at least one detection config field")

    for key, value in updates.items():
        try:
            cfg.set_detection_setting(key, value)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    return cfg.get_detection_settings()


@router.post("/detection-config/set-baseline", response_model=DetectionConfigResponse)
async def set_baseline(body: DetectionBaselineRequest):
    try:
        cfg.set_detection_baseline(body.baseline_angle, body.baseline_mud_weight)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return cfg.get_detection_settings()
