"""SimulatorController — manages the lifecycle of the internal simulator.

The simulator is now a thin wrapper around SimulatorDataSource. It holds
the asyncio task and exposes start/stop/mode controls. It has no knowledge
of detection logic, the WebSocket router, or the database — it simply
passes a data source to an IngestionPipeline when enabled.

The event bus is passed in at enable-time (from app.state.bus) so this
module has zero coupling to the application startup wiring.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from data_sources import SimulatorDataSource
from detection_engine import DetectionEngine
from interfaces import IEventBus
from pipeline import IngestionPipeline
from sensor_processor import SensorProcessor

SimulatorMode = Literal["normal", "kick", "loss"]

log = logging.getLogger("riglab.simulator")


class SimulatorController:
    def __init__(self) -> None:
        self._source = SimulatorDataSource(mode="normal", interval=1.0)
        self._task: asyncio.Task | None = None
        self.enabled = False

    def get_state(self) -> dict:
        return {
            "enabled": self.enabled,
            "mode": self._source.mode,
            "interval_seconds": self._source._interval,
        }

    def set_mode(self, mode: SimulatorMode) -> dict:
        self._source.mode = mode
        log.info("simulator mode → %s", mode)
        return self.get_state()

    async def set_enabled(self, enabled: bool, bus: IEventBus) -> dict:
        if enabled:
            await self._start(bus)
        else:
            await self._stop()
        return self.get_state()

    async def _start(self, bus: IEventBus) -> None:
        self.enabled = True
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(bus), name="riglab-simulator")
        log.info("simulator started (mode=%s)", self._source.mode)

    async def _stop(self) -> None:
        self.enabled = False
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        log.info("simulator stopped")

    async def _run(self, bus: IEventBus) -> None:
        detector = SensorProcessor(DetectionEngine())
        pipeline = IngestionPipeline(detector=detector, bus=bus)
        try:
            await pipeline.run(self._source)
        except asyncio.CancelledError:
            pass


simulator = SimulatorController()
