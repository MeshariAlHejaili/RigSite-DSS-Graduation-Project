from __future__ import annotations

import datetime
import json

from fastapi import APIRouter
from fastapi.responses import Response

from utils import database
from reports.generator import daily_pdf, incident_pdf

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


@router.post("/reports/incident")
async def report_incident():
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
    pdf = incident_pdf([_row_to_dict(row)] if row else [])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=incident_report.pdf"},
    )


@router.post("/reports/daily")
async def report_daily():
    pool = database.get_pool()
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM telemetry WHERE timestamp >= $1 ORDER BY timestamp DESC",
            since,
        )
    pdf = daily_pdf([_row_to_dict(row) for row in rows])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=daily_summary.pdf"},
    )
