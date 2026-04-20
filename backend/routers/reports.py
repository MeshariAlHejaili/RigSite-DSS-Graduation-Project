from __future__ import annotations

import datetime

from fastapi import APIRouter
from fastapi.responses import Response

from core.schemas import TelemetryCollectionResponse, storage_record_to_payload
from reports.generator import daily_pdf, incident_pdf
from utils import database

router = APIRouter()


async def _incident_records() -> list[dict]:
    pool = database.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM telemetry
            WHERE state IN ('KICK_RISK', 'LOSS_RISK')
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
    if row is None:
        return []
    return [storage_record_to_payload(dict(row))]


async def _daily_records() -> list[dict]:
    pool = database.get_pool()
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM telemetry WHERE timestamp >= $1 ORDER BY timestamp DESC",
            since,
        )
    return [storage_record_to_payload(dict(row)) for row in rows]


@router.get("/reports/incident/payload", response_model=TelemetryCollectionResponse)
async def report_incident_payload():
    records = await _incident_records()
    return {"count": len(records), "records": records}


@router.get("/reports/daily/payload", response_model=TelemetryCollectionResponse)
async def report_daily_payload():
    records = await _daily_records()
    return {"count": len(records), "records": records}


@router.post("/reports/incident")
async def report_incident():
    records = await _incident_records()
    pdf = incident_pdf(records)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=incident_report.pdf"},
    )


@router.post("/reports/daily")
async def report_daily():
    records = await _daily_records()
    pdf = daily_pdf(records)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=daily_summary.pdf"},
    )
