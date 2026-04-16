from __future__ import annotations

from fastapi import APIRouter, HTTPException

import config as cfg
import database

router = APIRouter()

ALLOWED_KEYS = set(cfg.PETE_KEYS)


@router.get("/config")
async def get_config():
    return cfg.get_pete_constants()


@router.post("/config")
async def update_config(body: dict):
    invalid = set(body.keys()) - ALLOWED_KEYS
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
