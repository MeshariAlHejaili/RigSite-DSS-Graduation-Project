from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter
from fastapi.responses import Response

from core.schemas import TelemetryCollectionResponse, storage_record_to_payload
from reports.generator import daily_pdf, incident_pdf
from utils import database
from utils.config import REPORT_TIMEZONE

router = APIRouter()


def _resolve_report_timezone() -> tuple[ZoneInfo, str]:
    try:
        return ZoneInfo(REPORT_TIMEZONE), REPORT_TIMEZONE
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC"), "UTC"


def _daily_window_for_now(
    now_utc: datetime.datetime | None = None,
) -> tuple[datetime.datetime, datetime.datetime, datetime.date, str]:
    tz, tz_name = _resolve_report_timezone()
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=datetime.timezone.utc)
    else:
        now_utc = now_utc.astimezone(datetime.timezone.utc)

    local_now = now_utc.astimezone(tz)
    day_start_local = datetime.datetime.combine(local_now.date(), datetime.time.min, tzinfo=tz)
    next_day_start_local = day_start_local + datetime.timedelta(days=1)
    return (
        day_start_local.astimezone(datetime.timezone.utc),
        next_day_start_local.astimezone(datetime.timezone.utc),
        local_now.date(),
        tz_name,
    )


async def _incident_records() -> list[dict]:
    pool = database.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH ordered AS (
                SELECT
                    t.*,
                    LAG(state) OVER (ORDER BY timestamp) AS prev_state
                FROM telemetry t
            ),
            tagged AS (
                SELECT
                    *,
                    CASE
                        WHEN state IN ('KICK_RISK', 'LOSS_RISK')
                         AND COALESCE(prev_state, 'NORMAL') NOT IN ('KICK_RISK', 'LOSS_RISK')
                        THEN 1
                        ELSE 0
                    END AS episode_start
                FROM ordered
            ),
            grouped AS (
                SELECT
                    *,
                    SUM(episode_start) OVER (ORDER BY timestamp) AS episode_id
                FROM tagged
            ),
            latest_episode AS (
                SELECT MAX(episode_id) AS episode_id
                FROM grouped
                WHERE state IN ('KICK_RISK', 'LOSS_RISK')
            )
            SELECT *
            FROM grouped
            WHERE episode_id = (SELECT episode_id FROM latest_episode)
              AND state IN ('KICK_RISK', 'LOSS_RISK')
            ORDER BY timestamp ASC
            """
        )
    if not rows:
        return []
    return [storage_record_to_payload(dict(row)) for row in rows]


async def _daily_records() -> tuple[list[dict], datetime.date, str]:
    pool = database.get_pool()
    day_start_utc, next_day_start_utc, local_date, tz_name = _daily_window_for_now()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM telemetry
            WHERE timestamp >= $1
              AND timestamp < $2
            ORDER BY timestamp DESC
            """,
            day_start_utc,
            next_day_start_utc,
        )
    return [storage_record_to_payload(dict(row)) for row in rows], local_date, tz_name


@router.get("/reports/incident/payload", response_model=TelemetryCollectionResponse)
async def report_incident_payload():
    records = await _incident_records()
    return {"count": len(records), "records": records}


@router.get("/reports/daily/payload", response_model=TelemetryCollectionResponse)
async def report_daily_payload():
    records, _, _ = await _daily_records()
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
    records, local_date, tz_name = await _daily_records()
    pdf = daily_pdf(records, report_date=local_date, report_timezone=tz_name)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=daily_summary.pdf"},
    )
