"""FastAPI application entry point and dependency-injection wiring.

Startup sequence:
  1. Init database pool
  2. Construct InMemoryEventBus
  3. Register DatabaseWriter and WebSocketBroadcaster as subscribers
  4. Store bus, broadcaster, and SimulatorController on app.state
     so routers and WebSocket handlers can resolve them without imports

All cross-layer wiring happens here and only here.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils import database
from core.event_bus import InMemoryEventBus
from core.simulator import SimulatorController
from core.subscribers import DatabaseWriter, WebSocketBroadcaster
from routers import websocket as ws_router
from routers import history as history_router
from routers import config as config_router
from routers import reports as reports_router
from routers import simulator as simulator_router
from routers import angle as angle_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="RigLab-AI Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await database.init_db()

    bus = InMemoryEventBus()
    db_writer = DatabaseWriter()
    broadcaster = WebSocketBroadcaster()

    bus.subscribe(db_writer.handle)
    bus.subscribe(broadcaster.handle)

    app.state.bus = bus
    app.state.broadcaster = broadcaster
    app.state.simulator = SimulatorController()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    sim: SimulatorController = app.state.simulator
    await sim._stop()
    await database.close_db()


app.include_router(ws_router.router)
app.include_router(history_router.router, prefix="/api/v1")
app.include_router(config_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(simulator_router.router, prefix="/api/v1")
app.include_router(angle_router.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict:
    db_ok = await database.is_connected()
    broadcaster: WebSocketBroadcaster = app.state.broadcaster
    return {
        "status": "ok",
        "db_connected": db_ok,
        "active_live_connections": broadcaster.connection_count,
    }
