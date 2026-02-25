"""
Generate dummy sensor data for RigLab-AI prototype testing.
Output: sensor_data.xlsx at project root (60 rows, 20 min at 20s interval).
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROWS = 60
INTERVAL_SEC = 20


def main():
    start = datetime(2025, 1, 1, 8, 0, 0)  # 08:00:00
    times = [start + timedelta(seconds=i * INTERVAL_SEC) for i in range(ROWS)]
    time_str = [t.strftime("%H:%M:%S") for t in times]

    mw = []
    gate_angle = []
    viscosity = []

    for i in range(ROWS):
        if i <= 20:
            # Normal: MW ~9.0, Gate_Angle 40–42, Viscosity ~50
            mw.append(round(9.0 + random.uniform(-0.05, 0.05), 2))
            gate_angle.append(round(random.uniform(40, 42), 2))
            viscosity.append(round(50 + random.uniform(-2, 2), 2))
        elif i <= 40:
            # Kick: Gate_Angle ~65, MW ~8.5
            mw.append(round(8.5 + random.uniform(-0.05, 0.05), 2))
            gate_angle.append(round(65 + random.uniform(-0.5, 0.5), 2))
            viscosity.append(round(50 + random.uniform(-2, 2), 2))
        else:
            # Loss: Gate_Angle ~10, MW ~9.5
            mw.append(round(9.5 + random.uniform(-0.05, 0.05), 2))
            gate_angle.append(round(10 + random.uniform(-0.5, 0.5), 2))
            viscosity.append(round(50 + random.uniform(-2, 2), 2))

    df = pd.DataFrame({
        "Time": time_str,
        "MW": mw,
        "Gate_Angle": gate_angle,
        "Viscosity": viscosity,
    })

    # Output to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    out_path = project_root / "sensor_data.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Generated {out_path} with 60 rows.")


if __name__ == "__main__":
    main()
