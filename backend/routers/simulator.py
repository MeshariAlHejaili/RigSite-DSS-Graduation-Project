from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from simulator import simulator

router = APIRouter()


class SimulatorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["normal", "kick", "loss"] | None = None
    enabled: bool | None = None


@router.get("/simulator")
async def get_simulator_state():
    return simulator.get_state()


@router.post("/simulator")
async def update_simulator_state(body: SimulatorUpdate):
    if body.mode is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="provide mode and/or enabled")
    if body.mode is not None and body.mode not in {"normal", "kick", "loss"}:
        raise HTTPException(status_code=400, detail="invalid simulator mode")
    if body.mode is not None:
        simulator.set_mode(body.mode)
    if body.enabled is not None:
        await simulator.set_enabled(body.enabled)
    return simulator.get_state()
