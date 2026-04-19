"""FastAPI app entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
from simulator import simulator
from routers import websocket as ws_router
from routers import history as history_router
from routers import config as config_router
from routers import reports as reports_router
from routers import simulator as simulator_router
from routers import angle as angle_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="RigLab-AI Backend", version="1.0")

# CORS: allow Vite dev server (5173) and any origin during dev
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


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await simulator.stop()
    await database.close_db()


# WebSocket routes are mounted without prefix
app.include_router(ws_router.router)

# REST routes under /api/v1
app.include_router(history_router.router, prefix="/api/v1")
app.include_router(config_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(simulator_router.router, prefix="/api/v1")
app.include_router(angle_router.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict:
    db_ok = await database.is_connected()
    return {
        "status": "ok",
        "db_connected": db_ok,
        "active_ingest_connections": len(ws_router.ingest_connections),
        "active_live_connections": len(ws_router.live_connections),
    }
