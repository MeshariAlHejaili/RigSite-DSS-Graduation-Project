from __future__ import annotations

import json

from fastapi import APIRouter, Query

import database

router = APIRouter()


def _row_to_dict(row) -> dict:
    record = dict(row)
    record["timestamp"] = record["timestamp"].isoformat().replace("+00:00", "Z")
    if isinstance(record.get("device_health"), str):
        record["device_health"] = json.loads(record["device_health"])
    record["flow_deviation_pct"] = record.pop("flow_deviation", None)
    record["decision_confidence"] = record.pop("decision_conf", None)
    record["processed_at"] = record["timestamp"]
    record.pop("id", None)
    return record


def _session_row_to_dict(row) -> dict:
    session = dict(row)
    session["started_at"] = session["started_at"].isoformat().replace("+00:00", "Z")
    if session.get("ended_at") is not None:
        session["ended_at"] = session["ended_at"].isoformat().replace("+00:00", "Z")
    session["record_count"] = int(session["record_count"])
    return session


@router.get("/telemetry/recent")
async def telemetry_recent(limit: int = Query(50, le=500)):
    pool = database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT $1", limit)
    return {"count": len(rows), "records": [_row_to_dict(row) for row in rows]}


@router.get("/telemetry/session")
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
    return {"count": len(rows), "records": [_row_to_dict(row) for row in rows]}


@router.get("/sessions")
async def sessions():
    pool = database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.started_at, s.ended_at, COUNT(t.id) AS record_count
            FROM sessions s
            LEFT JOIN telemetry t
              ON t.timestamp >= s.started_at
             AND (s.ended_at IS NULL OR t.timestamp <= s.ended_at)
            GROUP BY s.id
            ORDER BY s.started_at DESC
            """
        )
    return {"sessions": [_session_row_to_dict(row) for row in rows]}
