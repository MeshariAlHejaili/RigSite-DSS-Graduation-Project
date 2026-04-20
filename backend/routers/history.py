from __future__ import annotations

from fastapi import APIRouter, Query

from core.schemas import (
    SessionSummaryResponse,
    SessionsResponse,
    TelemetryCollectionResponse,
    storage_record_to_payload,
)
from utils import database

router = APIRouter()


def _session_row_to_dict(row) -> dict:
    session = dict(row)
    session["started_at"] = session["started_at"].isoformat().replace("+00:00", "Z")
    if session.get("ended_at") is not None:
        session["ended_at"] = session["ended_at"].isoformat().replace("+00:00", "Z")
    session["record_count"] = int(session["record_count"])
    return SessionSummaryResponse.model_validate(session).model_dump(mode="json")


@router.get("/telemetry/recent", response_model=TelemetryCollectionResponse)
async def telemetry_recent(limit: int = Query(50, le=500)):
    pool = database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT $1", limit)
    records = [storage_record_to_payload(dict(row)) for row in rows]
    return {"count": len(records), "records": records}


@router.get("/telemetry/session", response_model=TelemetryCollectionResponse)
async def telemetry_session(session_id: int):
    pool = database.get_pool()
    async with pool.acquire() as conn:
        session = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
        if session is None:
            return {"count": 0, "records": []}

        rows = await conn.fetch(
            """
            SELECT * FROM telemetry
            WHERE timestamp >= $1
              AND ($2::timestamptz IS NULL OR timestamp <= $2)
            ORDER BY timestamp DESC
            """,
            session["started_at"],
            session["ended_at"],
        )
    records = [storage_record_to_payload(dict(row)) for row in rows]
    return {"count": len(records), "records": records}


@router.get("/sessions", response_model=SessionsResponse)
async def sessions():
    pool = database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.started_at, s.ended_at, s.note, COUNT(t.id) AS record_count
            FROM sessions s
            LEFT JOIN telemetry t
              ON t.timestamp >= s.started_at
             AND (s.ended_at IS NULL OR t.timestamp <= s.ended_at)
            GROUP BY s.id
            ORDER BY s.started_at DESC
            """
        )
    return {"sessions": [_session_row_to_dict(row) for row in rows]}
