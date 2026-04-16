from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from simulator import simulator

router = APIRouter()


class SimulatorUpdate(BaseModel):
    mode: Literal["normal", "kick", "loss"]


@router.get("/simulator")
async def get_simulator_state():
    return simulator.get_state()


@router.post("/simulator")
async def update_simulator_state(body: SimulatorUpdate):
    if body.mode not in {"normal", "kick", "loss"}:
        raise HTTPException(status_code=400, detail="invalid simulator mode")
    return simulator.set_mode(body.mode)
