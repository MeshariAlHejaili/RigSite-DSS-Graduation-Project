from __future__ import annotations

import datetime
import io
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _doc(title: str) -> tuple:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated: {datetime.datetime.utcnow().isoformat()}Z", styles["Normal"]),
        Spacer(1, 20),
    ]
    return buffer, document, story, styles


def incident_pdf(records: list[dict]) -> bytes:
    buffer, document, story, styles = _doc("RigLab-AI - Critical Incident Snapshot")
    if not records:
        story.append(Paragraph("No anomaly records found.", styles["Normal"]))
    else:
        record = records[0]
        story.append(Paragraph(f"Latest anomaly: {record['state']}", styles["Heading2"]))
        story.append(Spacer(1, 10))
        table = Table(
            [["Field", "Value"]] + [[key, str(value)] for key, value in record.items()],
            colWidths=[180, 300],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ]
            )
        )
        story.append(table)
    document.build(story)
    return buffer.getvalue()


def daily_pdf(records: list[dict]) -> bytes:
    buffer, document, story, styles = _doc("RigLab-AI - Daily Summary Report")
    counts = Counter(record["state"] for record in records)
    story.append(Paragraph(f"Total records (last 24h): {len(records)}", styles["Normal"]))
    story.append(Spacer(1, 12))
    table = Table([["State", "Count"]] + [[key, str(value)] for key, value in sorted(counts.items())], colWidths=[200, 100])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return buffer.getvalue()
