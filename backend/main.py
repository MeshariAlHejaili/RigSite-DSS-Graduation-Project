"""
RigLab-AI Backend - Drilling monitoring prototype.
FastAPI app with Excel upload, situation logic, and WebSocket playback.
"""

import asyncio
import io
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import CalculatedData

# Rows back for "5 minutes ago" at 20-second interval
ROWS_5_MIN = 15
ANGLE_THRESHOLD_KICK = 15.0
ANGLE_THRESHOLD_LOSS = -15.0

app = FastAPI(title="RigLab-AI", description="Drilling monitoring prototype backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def compute_situation(current_angle: float, angle_5min_ago: Optional[float]) -> str:
    """
    Compare current Gate_Angle with value from 5 minutes ago (15 rows back).
    > 15 deg -> Kick, < -15 deg -> Loss, else Normal.
    """
    if angle_5min_ago is None:
        return "Normal"
    delta = current_angle - angle_5min_ago
    if delta > ANGLE_THRESHOLD_KICK:
        return "Kick"
    if delta < ANGLE_THRESHOLD_LOSS:
        return "Loss"
    return "Normal"


def parse_timestamp(ts) -> datetime:
    """Parse Excel time column to datetime."""
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        return pd.to_datetime(ts)
    return pd.to_datetime(ts)


@app.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accept an Excel file with columns: Time, MW, Gate_Angle, Viscosity.
    Compute situation per row (Kick/Loss/Normal from Gate_Angle delta vs 5 min ago)
    and save all rows to the database.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        return {"detail": "File must be an Excel file (.xlsx or .xls)"}

    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))

    required = {"Time", "MW", "Gate_Angle", "Viscosity"}
    missing = required - set(df.columns)
    if missing:
        return {"detail": f"Missing columns: {sorted(missing)}"}

    # Ensure we have numeric columns for angles
    df["Gate_Angle"] = pd.to_numeric(df["Gate_Angle"], errors="coerce")
    df = df.dropna(subset=["Gate_Angle"])

    angle_values: List[float] = df["Gate_Angle"].tolist()
    rows_to_insert: List[CalculatedData] = []

    for i in range(len(df)):
        row = df.iloc[i]
        angle_5min_ago = angle_values[i - ROWS_5_MIN] if i >= ROWS_5_MIN else None
        situation = compute_situation(float(angle_values[i]), angle_5min_ago)

        ts = parse_timestamp(row["Time"])
        mw = float(row["MW"])
        viscosity = float(row["Viscosity"])
        gate_angle = float(angle_values[i])

        rows_to_insert.append(
            CalculatedData(
                timestamp=ts,
                mw_ppg=mw,
                gate_angle=gate_angle,
                viscosity=viscosity,
                situation=situation,
            )
        )

    db.add_all(rows_to_insert)
    db.commit()
    return {
        "message": "File processed successfully",
        "rows_saved": len(rows_to_insert),
    }


@app.websocket("/ws")
async def websocket_stream(websocket: WebSocket):
    """
    On connect, load all saved calculated data and stream one point every 0.1 s
    to simulate live playback (timestamp, mw, viscosity, angle, situation).
    """
    await websocket.accept()

    db = next(get_db())
    try:
        records = (
            db.query(CalculatedData)
            .order_by(CalculatedData.id)
            .all()
        )
    finally:
        db.close()

    if not records:
        await websocket.send_json({"status": "no_data", "message": "No data in database. Upload an Excel file first."})
        await websocket.close()
        return

    for rec in records:
        try:
            ts = rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp)
            payload = {
                "timestamp": ts,
                "mw": rec.mw_ppg,
                "viscosity": rec.viscosity,
                "angle": rec.gate_angle,
                "situation": rec.situation,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.5)  # Slower for testing (0.1 in production)
        except WebSocketDisconnect:
            break

    await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
