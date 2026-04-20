from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from core.simulator import SimulatorController

router = APIRouter()


class SimulatorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["normal", "kick", "loss"] | None = None
    enabled: bool | None = None


@router.get("/simulator")
async def get_simulator_state(request: Request):
    sim: SimulatorController = request.app.state.simulator
    return sim.get_state()


@router.post("/simulator")
async def update_simulator_state(request: Request, body: SimulatorUpdate):
    if body.mode is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="provide mode and/or enabled")

    sim: SimulatorController = request.app.state.simulator
    bus = request.app.state.bus

    if body.mode is not None:
        sim.set_mode(body.mode)
    if body.enabled is not None:
        await sim.set_enabled(body.enabled, bus)

    return sim.get_state()
