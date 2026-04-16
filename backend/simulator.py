from __future__ import annotations

import asyncio
import logging
from typing import Literal

from anomaly_engine import AnomalyEngine, reset_active_engine, set_active_engine
from config import get_pete_constants
from processing import process_payload
from routers import websocket as websocket_router
from simulator_scenarios import kick, loss, normal

SimulatorMode = Literal["normal", "kick", "loss"]

log = logging.getLogger("riglab.simulator")


class InternalSimulator:
    def __init__(self) -> None:
        self.enabled = True
        self.mode: SimulatorMode = "normal"
        self.interval_seconds = 1.0
        self._task: asyncio.Task | None = None
        self._engine = AnomalyEngine()
        self._sample_index = 0
        self._scenarios = {
            "normal": normal,
            "kick": kick,
            "loss": loss,
        }

    def get_state(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "interval_seconds": self.interval_seconds,
        }

    def set_mode(self, mode: SimulatorMode) -> dict:
        self.mode = mode
        log.info("internal simulator mode changed to %s", mode)
        return self.get_state()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="riglab-internal-simulator")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            scenario_fn = self._scenarios[self.mode]
            raw_payload = scenario_fn(self._sample_index)
            self._sample_index += 1
            token = set_active_engine(self._engine)
            try:
                state = process_payload(raw_payload, get_pete_constants())
            finally:
                reset_active_engine(token)
            await websocket_router.persist_and_broadcast(state)
            await asyncio.sleep(self.interval_seconds)


simulator = InternalSimulator()
