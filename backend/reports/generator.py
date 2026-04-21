from __future__ import annotations

import datetime
import io
from collections import Counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RISK_STATES = {"KICK_RISK", "LOSS_RISK"}
STATE_DISPLAY_ORDER = ("NORMAL", "KICK_RISK", "LOSS_RISK", "SENSOR_FAULT")
VARIABLE_SPECS = (
    ("gate_angle", "Gate Angle (deg)"),
    ("viscosity", "Viscosity (Pa*s)"),
    ("normal_mud_weight", "Mud Weight (ppg)"),
    ("mud_weight_with_cuttings", "Mud Weight w/ Cuttings (ppg)"),
)


def _doc(title: str) -> tuple:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')}", styles["Normal"]),
        Spacer(1, 20),
    ]
    return buffer, document, story, styles


def _safe_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _to_utc_datetime(value: object) -> datetime.datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    return None


def _records_sorted(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda record: _to_utc_datetime(record.get("timestamp")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))


def _format_number(value: object, *, default: str = "N/A") -> str:
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    rendered = f"{numeric:.4f}".rstrip("0").rstrip(".")
    return rendered if rendered else "0"


def _format_timestamp(value: object, tz_name: str = "UTC") -> str:
    dt = _to_utc_datetime(value)
    if dt is None:
        return "N/A"
    zone = _safe_zoneinfo(tz_name)
    local_dt = dt.astimezone(zone)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _duration_text(start_value: object, end_value: object) -> str:
    started = _to_utc_datetime(start_value)
    ended = _to_utc_datetime(end_value)
    if started is None or ended is None:
        return "N/A"
    delta = ended - started
    if delta.total_seconds() < 0:
        return "N/A"
    return str(delta).split(".")[0]


def _numeric_values(records: list[dict], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        raw = record.get(field)
        if raw is None:
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return values


def _variable_stat_rows(records: list[dict]) -> list[list[str]]:
    rows: list[list[str]] = [["Variable", "Min", "Max", "Samples Used"]]
    for field, label in VARIABLE_SPECS:
        values = _numeric_values(records, field)
        if values:
            min_value = _format_number(min(values))
            max_value = _format_number(max(values))
        elif field == "mud_weight_with_cuttings":
            min_value = "Not specified"
            max_value = "Not specified"
        else:
            min_value = "N/A"
            max_value = "N/A"
        rows.append([label, min_value, max_value, str(len(values))])
    return rows


def _risk_episodes(records: list[dict]) -> list[list[dict]]:
    episodes: list[list[dict]] = []
    current: list[dict] = []
    for record in _records_sorted(records):
        state = record.get("state")
        if state in RISK_STATES:
            current.append(record)
            continue
        if current:
            episodes.append(current)
            current = []
    if current:
        episodes.append(current)
    return episodes


def _incident_kpi_rows(records: list[dict], report_timezone: str) -> list[list[str]]:
    episodes = _risk_episodes(records)
    kick_episodes = 0
    loss_episodes = 0
    for episode in episodes:
        episode_states = {row.get("state") for row in episode}
        if "KICK_RISK" in episode_states:
            kick_episodes += 1
        if "LOSS_RISK" in episode_states:
            loss_episodes += 1

    risky_records = [record for record in records if record.get("state") in RISK_STATES]
    risky_pct = (len(risky_records) / len(records) * 100.0) if records else 0.0
    latest_incident_ts = risky_records[-1]["timestamp"] if risky_records else None

    return [
        ["KPI", "Value"],
        ["Kick episodes", str(kick_episodes)],
        ["Loss episodes", str(loss_episodes)],
        ["Risky-record %", f"{risky_pct:.2f}%"],
        ["Latest incident time", _format_timestamp(latest_incident_ts, report_timezone) if latest_incident_ts else "N/A"],
    ]


def _incident_type(records: list[dict]) -> str:
    states = {record.get("state") for record in records if record.get("state") in RISK_STATES}
    if states == {"KICK_RISK"}:
        return "KICK_RISK"
    if states == {"LOSS_RISK"}:
        return "LOSS_RISK"
    return "MIXED"


def _styled_table(rows: list[list[str]], col_widths: list[int]) -> Table:
    table = Table(rows, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def incident_pdf(records: list[dict]) -> bytes:
    buffer, document, story, styles = _doc("RigLab-AI - Critical Incident Snapshot")
    if not records:
        story.append(Paragraph("No kick/loss incidents were found.", styles["Normal"]))
        document.build(story)
        return buffer.getvalue()

    ordered_records = _records_sorted(records)
    first_record = ordered_records[0]
    last_record = ordered_records[-1]
    incident_type = _incident_type(ordered_records)

    story.append(Paragraph(f"Latest incident episode: {incident_type}", styles["Heading2"]))
    story.append(Spacer(1, 8))

    episode_window_rows = [
        ["Field", "Value"],
        ["Episode start", _format_timestamp(first_record.get("timestamp"))],
        ["Episode end", _format_timestamp(last_record.get("timestamp"))],
        ["Duration", _duration_text(first_record.get("timestamp"), last_record.get("timestamp"))],
        ["Samples in episode", str(len(ordered_records))],
    ]
    story.append(_styled_table(episode_window_rows, [180, 300]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Episode min/max", styles["Heading3"]))
    story.append(_styled_table(_variable_stat_rows(ordered_records), [200, 95, 95, 90]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Final reading snapshot", styles["Heading3"]))
    snapshot_rows = [
        ["Field", "Value"],
        ["Timestamp", _format_timestamp(last_record.get("timestamp"))],
        ["State", str(last_record.get("state", "N/A"))],
        ["Decision confidence", _format_number(last_record.get("decision_confidence"))],
        ["Sensor status", str(last_record.get("sensor_status", "N/A"))],
        ["Angle deviation", _format_number(last_record.get("angle_deviation"))],
        ["Mud-weight deviation %", _format_number(last_record.get("mud_weight_deviation_pct"))],
        ["Gate angle", _format_number(last_record.get("gate_angle"))],
        ["Mud weight", _format_number(last_record.get("normal_mud_weight"))],
        ["Mud weight w/ cuttings", _format_number(last_record.get("mud_weight_with_cuttings"), default="Not specified")],
        ["Viscosity", _format_number(last_record.get("viscosity"))],
    ]
    story.append(_styled_table(snapshot_rows, [200, 280]))

    document.build(story)
    return buffer.getvalue()


def daily_pdf(
    records: list[dict],
    *,
    report_date: datetime.date | None = None,
    report_timezone: str = "UTC",
) -> bytes:
    buffer, document, story, styles = _doc("RigLab-AI - Daily Summary Report")
    ordered_records = _records_sorted(records)
    counts = Counter(record.get("state", "UNKNOWN") for record in ordered_records)

    if report_date is None:
        today_local = datetime.datetime.now(_safe_zoneinfo(report_timezone)).date()
        report_date = today_local

    story.append(Paragraph(f"Report day ({report_timezone}): {report_date.isoformat()}", styles["Normal"]))
    story.append(Paragraph(f"Total records (current local day): {len(ordered_records)}", styles["Normal"]))
    story.append(Spacer(1, 12))

    state_rows: list[list[str]] = [["State", "Count"]]
    for state in STATE_DISPLAY_ORDER:
        state_rows.append([state, str(counts.get(state, 0))])
    extra_states = sorted(state for state in counts.keys() if state not in STATE_DISPLAY_ORDER)
    for state in extra_states:
        state_rows.append([state, str(counts[state])])

    story.append(Paragraph("State distribution", styles["Heading3"]))
    story.append(_styled_table(state_rows, [240, 120]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Variable min/max", styles["Heading3"]))
    story.append(_styled_table(_variable_stat_rows(ordered_records), [200, 95, 95, 90]))

    document.build(story)
    return buffer.getvalue()
