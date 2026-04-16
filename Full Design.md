# RigLab-AI — Laptop Server Phase: Master Design Document
# Version: 1.0 | Scope: Backend + Frontend + Mock Data Only
# Target: Autonomous AI Coding Agent Execution

---

## AGENT INSTRUCTIONS (READ FIRST)

You are building the complete laptop-side of the RigLab-AI system.
The physical Raspberry Pi, real sensors, and real camera are NOT part of this phase.
You will simulate them with a mock data generator that produces realistic payloads.

Rules you must follow without exception:
- Follow every step in Section 12 in strict order. Do not skip or reorder steps.
- After every major step marked [PAUSE FOR USER TEST], stop and output the exact
  message: "STEP N COMPLETE — Please test now and confirm before I continue."
  Do not proceed until the user confirms.
- Never invent an endpoint, field name, or file that is not defined in this document.
- If something is ambiguous, output a question and wait. Do not guess and proceed.
- Keep all code in the exact files specified in Section 3. Do not create extra files.
- All Python dependencies must be pinned in requirements.txt.
- All JS dependencies must be installed via npm and locked in package-lock.json.

---

## 1. SYSTEM OVERVIEW

RigLab-AI monitors a mud return line on an oil drilling rig. It detects two anomalies:
- KICK_RISK: actual flow exceeds expected flow by more than 15% (formation fluid influx)
- LOSS_RISK: actual flow is below expected flow by more than 15% (fluid loss into formation)
- NORMAL: deviation is within ±15%

In this laptop phase, a mock generator replaces the Raspberry Pi. It produces the same
JSON payload that the real Pi will eventually send. The backend processes it identically.
The frontend displays it identically. The only thing that changes in the Pi phase is the
source of the data — the rest of the system is untouched.

Data flow in this phase:

```text
  [Mock Generator (Python script)]
          |
          | WebSocket (ws://localhost:8000/ws/ingest)
          v
  [FastAPI Backend]
          |-- processes payload (9-step pipeline)
          |-- writes to PostgreSQL
          |-- broadcasts processed state
          v
  [React Frontend]  <-- WebSocket (ws://localhost:8000/ws/live)
          |
          | displays live charts, state badge, raw numbers table
```

---

## 2. TECHNOLOGY STACK

### Backend
- Language:        Python 3.11+
- Framework:       FastAPI
- WebSocket:       FastAPI native WebSocket support (starlette)
- Database:        PostgreSQL 15 with TimescaleDB extension
- ORM / DB driver: asyncpg (async PostgreSQL driver, no ORM)
- Report gen:      ReportLab (PDF generation)
- Containerisation: Docker + docker-compose
- Process runner:  Uvicorn

### Frontend
- Framework:       React 18 (via Vite, NOT Create React App)
- Charts:          Recharts
- WebSocket:       Native browser WebSocket API
- Styling:         Plain CSS (no Tailwind, no UI library — keep it simple)
- Build tool:      Vite

### Mock Generator
- Language:        Python 3.11+ (same virtualenv as backend)
- Protocol:        WebSocket client using the `websockets` library

### Infrastructure
- docker-compose manages: PostgreSQL + TimescaleDB, FastAPI server
- Frontend runs via: `npm run dev` (Vite dev server on port 5173)
- Mock generator runs via: `python mock/generator.py`

---

## 3. DIRECTORY STRUCTURE

Recreate this exact tree. Do not add or remove files.

```text
riglab-ai/
│
├── docker-compose.yml
├── .env
├── README.md
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # env vars, constants, DB connection
│   ├── database.py              # asyncpg pool setup, table init
│   ├── models.py                # Python dataclasses for payloads and DB records
│   ├── processing.py            # The 9-step processing pipeline
│   ├── classifier.py            # State classifier (NORMAL/KICK_RISK/LOSS_RISK)
│   ├── anomaly_engine.py        # Sustained-deviation tracker (N-sample window)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── websocket.py         # /ws/ingest and /ws/live endpoints
│   │   ├── history.py           # REST: recent records, session list
│   │   ├── config.py            # REST: read/update PETE constants
│   │   └── reports.py           # REST: trigger and download PDF reports
│   └── reports/
│       └── generator.py         # ReportLab PDF builder
│
├── mock/
│   ├── generator.py             # Mock data generator (simulates the Raspberry Pi)
│   └── scenarios.py             # Named scenarios: normal, kick, loss, drift
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/
        │   └── socket.js        # WebSocket singleton manager
        ├── components/
        │   ├── StateBadge.jsx   # NORMAL / KICK_RISK / LOSS_RISK indicator
        │   ├── FlowChart.jsx    # Actual vs Expected flow line chart
        │   ├── PressureChart.jsx# Pressure differential line chart
        │   ├── AngleChart.jsx   # Gate angle over time line chart
        │   ├── DataTable.jsx    # Last 20 raw records table
        │   └── ConnectionStatus.jsx # WebSocket connection indicator
        └── styles/
            └── app.css
```

---

## 4. ENVIRONMENT VARIABLES

Create `.env` in the project root with exactly these keys:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=riglab
POSTGRES_USER=riglab_user
POSTGRES_PASSWORD=riglab_pass

# TimescaleDB connection string (used by backend)
DATABASE_URL=postgresql://riglab_user:riglab_pass@localhost:5432/riglab

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Processing constants (PETE — can be overridden via dashboard)
FLOW_BASELINE=10.0        # expected flow at 90-degree gate angle (L/min)
ANOMALY_THRESHOLD=0.15    # 15% deviation triggers state change
ANOMALY_WINDOW=3          # number of consecutive breaching samples before state flips
```

---

## 5. DATA SCHEMAS

### 5.1 Raw Inbound Payload (Mock Generator → Backend via WebSocket)

This is exactly what the real Raspberry Pi will send in the hardware phase.
The mock generator must produce this schema faithfully.

```json
{
  "timestamp": 1713200000.123,
  "pressure1": 4.82,
  "pressure2": 3.91,
  "flow": 9.4,
  "gate_angle": 72.5,
  "angle_confidence": 0.91,
  "device_health": {
    "pressure_sensor_ok": true,
    "flow_sensor_ok": true,
    "camera_ok": true
  }
}
```

Field definitions:
- timestamp:          Unix timestamp (float, seconds since epoch)
- pressure1:          Upstream pressure in bar (float, range 0.0–20.0)
- pressure2:          Downstream pressure in bar (float, range 0.0–20.0)
- flow:               Measured volumetric flow in L/min (float, range 0.0–30.0)
- gate_angle:         Gate opening angle in degrees (float, range 0.0–90.0)
- angle_confidence:   CV confidence score (float, range 0.0–1.0)
- device_health:      Object with three boolean flags

### 5.2 Processed State (Backend → Frontend via WebSocket, and stored in DB)

After the 9-step pipeline, the backend broadcasts and persists this object:

```json
{
  "timestamp": 1713200000.123,
  "pressure1": 4.82,
  "pressure2": 3.91,
  "flow": 9.4,
  "gate_angle": 72.5,
  "angle_confidence": 0.91,
  "device_health": {
    "pressure_sensor_ok": true,
    "flow_sensor_ok": true,
    "camera_ok": true
  },
  "pressure_diff": 0.91,
  "expected_flow": 8.06,
  "flow_deviation_pct": 16.62,
  "state": "KICK_RISK",
  "decision_confidence": 0.87,
  "sensor_status": "ALL_OK",
  "processed_at": "2024-04-15T18:13:20.123Z"
}
```

Additional field definitions (derived by backend):
- pressure_diff:       P1 − P2 (float, bar)
- expected_flow:       FLOW_BASELINE × (gate_angle / 90.0) (float, L/min)
- flow_deviation_pct:  (flow − expected_flow) / expected_flow × 100 (float, %)
- state:               One of: "NORMAL", "KICK_RISK", "LOSS_RISK"
- decision_confidence: min(angle_confidence, 1.0 − |flow_deviation_pct| / 100) clamped to [0,1]
- sensor_status:       "ALL_OK" | "PRESSURE_FAULT" | "FLOW_FAULT" | "CAMERA_FAULT" | "MULTI_FAULT"
- processed_at:        ISO 8601 UTC string

### 5.3 Database Schema

Table name: `telemetry`
This is a TimescaleDB hypertable partitioned by timestamp.

```sql
CREATE TABLE IF NOT EXISTS telemetry (
    id               BIGSERIAL,
    timestamp        TIMESTAMPTZ NOT NULL,
    pressure1        FLOAT NOT NULL,
    pressure2        FLOAT NOT NULL,
    flow             FLOAT NOT NULL,
    gate_angle       FLOAT,
    angle_confidence FLOAT,
    pressure_diff    FLOAT NOT NULL,
    expected_flow    FLOAT NOT NULL,
    flow_deviation   FLOAT NOT NULL,
    state            VARCHAR(12) NOT NULL,
    decision_conf    FLOAT NOT NULL,
    sensor_status    VARCHAR(20) NOT NULL,
    device_health    JSONB NOT NULL
);

SELECT create_hypertable('telemetry', 'timestamp', if_not_exists => TRUE);
```

Table name: `pete_constants`

```sql
CREATE TABLE IF NOT EXISTS pete_constants (
    key   VARCHAR(64) PRIMARY KEY,
    value FLOAT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO pete_constants (key, value) VALUES
    ('flow_baseline', 10.0),
    ('anomaly_threshold', 0.15),
    ('anomaly_window', 3)
ON CONFLICT (key) DO NOTHING;
```

Table name: `sessions`

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id         BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at   TIMESTAMPTZ,
    note       TEXT
);
```

---

## 6. API SPECIFICATION

All REST endpoints are prefixed with `/api/v1`.
All responses are JSON unless noted (PDF download is binary).
All timestamps in responses are ISO 8601 UTC strings.

### 6.1 WebSocket Endpoints

**WS /ws/ingest**
- Purpose: Raspberry Pi (or mock generator) connects here to stream raw payloads.
  Backend runs the 9-step pipeline on each received message.
  Backend does NOT echo back to this socket.
- Message format: Raw JSON string matching Section 5.1 schema.
- On parse error: backend logs the error, sends back `{"error": "invalid_payload"}`, continues.

**WS /ws/live**
- Purpose: Frontend connects here to receive processed state in real time.
  Backend broadcasts every processed state object to all connected `/ws/live` clients.
- Message format: JSON string matching Section 5.2 schema.
- On client disconnect: remove from broadcast set silently.

### 6.2 REST Endpoints

**GET /api/v1/health**
Response 200:
```json
{
  "status": "ok",
  "db_connected": true,
  "active_ingest_connections": 1,
  "active_live_connections": 2
}
```

**GET /api/v1/telemetry/recent?limit=50**
Returns the most recent N processed records from the DB, newest first.
Default limit: 50. Max limit: 500.
Response 200:
```json
{
  "count": 50,
  "records": [ "<array of Section 5.2 objects>" ]
}
```

**GET /api/v1/telemetry/session?session_id=1**
Returns all records belonging to a given session ID.
Response 200: same shape as `/recent`

**GET /api/v1/sessions**
Returns list of all logging sessions.
Response 200:
```json
{
  "sessions": [
    { "id": 1, "started_at": "...", "ended_at": "...", "record_count": 120 }
  ]
}
```

**GET /api/v1/config**
Returns current PETE constants from `pete_constants` table.
Response 200:
```json
{
  "flow_baseline": 10.0,
  "anomaly_threshold": 0.15,
  "anomaly_window": 3
}
```

**POST /api/v1/config**
Updates one or more PETE constants. Triggers in-memory cache reload.
Request body:
```json
{
  "flow_baseline": 12.0
}
```
Response 200:
```json
{
  "updated": ["flow_baseline"],
  "current": { "flow_baseline": 12.0, "anomaly_threshold": 0.15, "anomaly_window": 3 }
}
```

**POST /api/v1/reports/incident**
Generates a Critical Incident Snapshot PDF for the most recent anomaly event.
Response 200: PDF binary with `Content-Disposition: attachment; filename=incident_report.pdf`

**POST /api/v1/reports/daily**
Generates a Daily Summary PDF for all records in the past 24 hours.
Response 200: PDF binary with `Content-Disposition: attachment; filename=daily_summary.pdf`

---

## 7. BACKEND PROCESSING PIPELINE (9 Steps)

Implement this exactly in `backend/processing.py`.
This function receives a raw payload dict and returns a processed state dict.
It must be a pure function — no side effects. DB writes happen in the router after this returns.

```python
def process_payload(raw: dict, pete: dict) -> dict:

  # Step 1 — Build unified state object
  # Copy all fields from raw into a working dict.
  # Add fields: pressure_diff=None, expected_flow=None, flow_deviation_pct=None,
  #             state=None, decision_confidence=None, sensor_status=None, processed_at=None

  # Step 2 — Validate signal quality
  # Check presence of: pressure1, pressure2, flow, gate_angle, timestamp.
  # Check ranges:
  #   pressure1, pressure2: must be 0.0–20.0 bar
  #   flow: must be 0.0–30.0 L/min
  #   gate_angle: must be 0.0–90.0 degrees
  #   angle_confidence: must be 0.0–1.0
  # If any required field is missing or out of range:
  #   Set sensor_status to appropriate fault code (see Section 5.2 field definitions).
  #   Set state to "SENSOR_FAULT".
  #   Set processed_at to current UTC time.
  #   Return immediately — do not continue to steps 3–9.

  # Step 3 — Determine sensor_status
  # If all device_health flags are True: sensor_status = "ALL_OK"
  # If only pressure flags False: sensor_status = "PRESSURE_FAULT"
  # If only flow flag False: sensor_status = "FLOW_FAULT"
  # If only camera flag False: sensor_status = "CAMERA_FAULT"
  # If multiple flags False: sensor_status = "MULTI_FAULT"

  # Step 4 — Compute derived values
  # pressure_diff = round(pressure1 − pressure2, 4)

  # Step 5 — Estimate expected flow from gate angle
  # expected_flow = round(pete["flow_baseline"] × (gate_angle / 90.0), 4)

  # Step 6 — Compute flow deviation
  # If expected_flow == 0:
  #   flow_deviation_pct = 0.0
  # Else:
  #   flow_deviation_pct = round((flow − expected_flow) / expected_flow × 100, 4)

  # Step 7 — Classify state (via anomaly_engine, not directly here)
  # Call anomaly_engine.evaluate(flow_deviation_pct, pete["anomaly_threshold"], pete["anomaly_window"])
  # This returns one of: "NORMAL", "KICK_RISK", "LOSS_RISK"
  # Assign result to state.

  # Step 8 — Compute decision_confidence
  # raw_conf = min(angle_confidence, 1.0 − abs(flow_deviation_pct) / 100.0)
  # decision_confidence = round(max(0.0, min(1.0, raw_conf)), 4)

  # Step 9 — Finalise
  # processed_at = current UTC datetime as ISO 8601 string
  # Return the complete processed state dict.
```

### Anomaly Engine (`backend/anomaly_engine.py`)
The state classifier must NOT flip on a single sample breach.
It must see N consecutive breaching samples before changing state.
N is the `anomaly_window` PETE constant (default: 3).

```python
class AnomalyEngine:
  # - Maintains a rolling deque of the last N deviation values.
  # - evaluate(deviation_pct, threshold, window):
  #     Append deviation_pct to the deque.
  #     If len(deque) < window: return "NORMAL" (not enough history yet)
  #     If ALL values in deque > +threshold×100: return "KICK_RISK"
  #     If ALL values in deque < -threshold×100: return "LOSS_RISK"
  #     Otherwise: return "NORMAL"

  # - There is ONE AnomalyEngine instance per active ingest connection.
  #   It is created when the /ws/ingest connection opens and destroyed when it closes.
  #   This ensures state history is per-session, not global.
```

---

## 8. MOCK DATA GENERATOR

File: `mock/generator.py`
File: `mock/scenarios.py`

### 8.1 Scenarios (`mock/scenarios.py`)
Define these named scenarios as functions that return a raw payload dict.
Each scenario introduces realistic noise on top of a base state.

**SCENARIOS:**

1. **normal(t)**
   - gate_angle: 60.0 + noise(±2°)
   - flow: 6.5 + noise(±0.3 L/min)         ← slightly below 60/90 × 10 = 6.67, within 15%
   - pressure1: 5.0 + noise(±0.1 bar)
   - pressure2: 4.0 + noise(±0.1 bar)
   - angle_confidence: 0.90 + noise(±0.05)
   - device_health: all True

2. **kick(t)**
   - gate_angle: 60.0 + noise(±1°)
   - flow: 8.5 + noise(±0.2 L/min)         ← ~27% above expected 6.67 → KICK_RISK
   - pressure1: 5.5 + noise(±0.15 bar)
   - pressure2: 4.0 + noise(±0.1 bar)
   - angle_confidence: 0.88 + noise(±0.04)
   - device_health: all True

3. **loss(t)**
   - gate_angle: 60.0 + noise(±1°)
   - flow: 4.5 + noise(±0.2 L/min)         ← ~33% below expected 6.67 → LOSS_RISK
   - pressure1: 4.5 + noise(±0.1 bar)
   - pressure2: 3.8 + noise(±0.1 bar)
   - angle_confidence: 0.85 + noise(±0.05)
   - device_health: all True

4. **drift(t)**
   - Starts as normal, linearly increases flow over 60 samples until it breaches 15%.
   - Useful for testing the anomaly_window requirement.

5. **camera_fault(t)**
   - Same as normal for sensors.
   - gate_angle: None
   - angle_confidence: 0.0
   - device_health: `{"pressure_sensor_ok": True, "flow_sensor_ok": True, "camera_ok": False}`

All scenarios use:
- `timestamp: time.time()`
- `noise(±x): random.uniform(-x, x)`

### 8.2 Generator Script (`mock/generator.py`)
Behaviour:
- Connects to `ws://localhost:8000/ws/ingest`
- Accepts a command-line argument `--scenario` (default: "normal")
  Valid values: `normal`, `kick`, `loss`, `drift`, `camera_fault`, `cycle`
- "cycle" scenario: runs normal for 20 samples, then kick for 10, then loss for 10, repeat.
- Sends one payload per second (configurable via `--interval`, default 1.0)
- Prints each sent payload to stdout as formatted JSON for debugging
- On connection failure: retries every 3 seconds, prints "Retrying connection..."
- Runs until Ctrl+C

CLI usage:
```bash
python mock/generator.py --scenario kick --interval 1.0
```

---

## 9. FRONTEND SPECIFICATION

### 9.1 Layout
Single-page application. No routing needed. Layout is top-to-bottom:

```text
┌─────────────────────────────────────────────────────┐
│  HEADER: "RigLab-AI Monitor"  |  [● LIVE] or [✕ DISCONNECTED]  │
├─────────────────────────────────────────────────────┤
│  STATE BADGE (full width, colour-coded)              │
│  e.g.  ⚠  KICK RISK  |  Deviation: +16.6%          │
├──────────────────────┬──────────────────────────────┤
│  Flow Chart          │  Pressure Chart              │
│  (actual vs expected)│  (ΔP over time)              │
├──────────────────────┴──────────────────────────────┤
│  Gate Angle Chart (over time)                        │
├─────────────────────────────────────────────────────┤
│  Raw Data Table (last 20 records)                    │
└─────────────────────────────────────────────────────┘
```

### 9.2 Component Specifications

**StateBadge.jsx**
- Reads `state` field from latest processed message.
- NORMAL:    green background,  text "NORMAL — System Stable"
- KICK_RISK: red background,    text "⚠ KICK RISK — Flow High by X%"
- LOSS_RISK: amber background,  text "⚠ LOSS RISK — Flow Low by X%"
- SENSOR_FAULT: grey background, text "⚠ SENSOR FAULT — Check Hardware"
- Font size: large (at least 20px). Badge should be unmissable.
- Also display: timestamp of last update, decision_confidence as percentage.

**FlowChart.jsx**
- Recharts LineChart.
- X-axis: timestamp (last 60 data points, formatted as HH:MM:SS).
- Y-axis: flow in L/min.
- Two lines:
  - "Actual Flow" (blue) — the `flow` field
  - "Expected Flow" (dashed grey) — the `expected_flow` field
- Tooltip shows both values and deviation percentage.
- Reference band or reference lines at ±15% of expected flow.

**PressureChart.jsx**
- Recharts LineChart.
- X-axis: timestamp (last 60 data points).
- Y-axis: pressure in bar.
- Two lines:
  - "P1 Upstream" (dark blue)
  - "P2 Downstream" (light blue)
- One derived line: "ΔP" (red dashed) — `pressure_diff` field.

**AngleChart.jsx**
- Recharts LineChart.
- X-axis: timestamp (last 60 data points).
- Y-axis: degrees (0–90).
- One line: "Gate Angle" (orange).
- Render `angle_confidence` as a shaded area below the line (opacity proportional to confidence).

**DataTable.jsx**
- Shows last 20 records, newest at top.
- Columns: Time | P1 | P2 | ΔP | Flow | Expected | Deviation% | Angle | State
- Row background colour matches state (green/red/amber/grey at low opacity).
- Numbers rounded to 2 decimal places.

**ConnectionStatus.jsx**
- Green dot + "LIVE" when WebSocket is connected.
- Red dot + "DISCONNECTED — Reconnecting..." when not connected.
- Displays count of records received in current session.

### 9.3 WebSocket Client (`api/socket.js`)
- Singleton pattern: one WebSocket instance for the whole app.
- Connects to `ws://localhost:8000/ws/live` on mount.
- On message: parse JSON, call registered listener callbacks.
- On close/error: attempt reconnect every 3 seconds, max 10 attempts.
- After 10 failed attempts: stop retrying, set status to "FAILED".
- Expose: `connect()`, `disconnect()`, `onMessage(callback)`, `getStatus()`

### 9.4 Data Buffer (`App.jsx`)
- Maintain a rolling buffer of the last 60 processed records in React state.
- Each new WebSocket message appends to the buffer; if buffer exceeds 60, drop the oldest.
- Pass the full buffer to chart components; charts handle their own windowing.
- Pass only the latest record to `StateBadge`.
- Pass the last 20 records to `DataTable`.

---

## 10. DOCKER CONFIGURATION

`docker-compose.yml`
```yaml
version: '3.8'
services:
  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: riglab
      POSTGRES_USER: riglab_user
      POSTGRES_PASSWORD: riglab_pass
    ports:
      - "5432:5432"
    volumes:
      - riglab_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U riglab_user -d riglab"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  riglab_pgdata:
```

`backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 11. BACKEND REQUIREMENTS (`backend/requirements.txt`)

```text
fastapi==0.111.0
uvicorn[standard]==0.29.0
asyncpg==0.29.0
websockets==12.0
python-dotenv==1.0.1
reportlab==4.1.0
pydantic==2.7.1
```

---

## 12. AGENT IMPLEMENTATION STEPS

Follow these steps in strict order.
Each step has a clear completion condition.
Do not begin the next step until the current one is complete and verified.

### STEP 1 — Project Scaffold & Infrastructure
Actions:
- Create the full directory tree from Section 3. Create all files as empty stubs.
- Create `.env` with all variables from Section 4.
- Create `docker-compose.yml` from Section 10.
- Create `backend/Dockerfile` from Section 10.
- Create `backend/requirements.txt` from Section 11.
- In `backend/config.py`: load all env vars using python-dotenv. Expose them as module-level constants. Define the in-memory PETE constants cache as a dict.
- In `backend/database.py`: implement `init_db()` async function that:
  - Creates an asyncpg connection pool stored as a module-level variable.
  - Executes the three CREATE TABLE statements from Section 5.3.
  - Executes the SELECT create_hypertable call.
  - Inserts default pete_constants rows.
- In `backend/main.py`: create the FastAPI app, call `init_db()` on startup via `@app.on_event("startup")`. Mount all routers. Add CORS middleware allowing all origins (needed for Vite dev server on port 5173).
- Run `docker-compose up -d` and verify DB starts healthy.
- Run `uvicorn main:app --reload` and verify the server starts without errors.
- Hit `GET /api/v1/health`. Verify response shows `db_connected: true`.

**[PAUSE FOR USER TEST]**
Output: "STEP 1 COMPLETE — Please verify: (1) docker-compose up runs with no errors, (2) GET http://localhost:8000/api/v1/health returns db_connected: true. Confirm before I continue."

### STEP 2 — Mock Data Generator
Actions:
- Implement `mock/scenarios.py` with all 5 scenario functions from Section 8.1. Each function must return a dict matching the Section 5.1 schema exactly.
- Implement `mock/generator.py` from Section 8.2:
  - Parse `--scenario` and `--interval` CLI args.
  - Implement the "cycle" meta-scenario.
  - Connect to `ws://localhost:8000/ws/ingest`.
  - Send one payload per interval, print to stdout.
  - Implement retry logic.
- At this point, `/ws/ingest` does not need to do anything except accept the connection. Add a stub WebSocket endpoint in `backend/routers/websocket.py` that accepts and prints received messages to the server log.
- Run: `python mock/generator.py --scenario normal`
- Verify payloads appear in the server log, formatted correctly.

**[PAUSE FOR USER TEST]**
Output: "STEP 2 COMPLETE — Please verify: (1) mock generator connects without errors, (2) server log shows incoming JSON payloads every second matching the schema. Confirm before I continue."

### STEP 3 — Processing Pipeline & Anomaly Engine
Actions:
- Implement `backend/anomaly_engine.py` exactly as specified in Section 7. Use `collections.deque(maxlen=window)`.
- Implement `backend/processing.py` with the `process_payload(raw, pete)` function following all 9 steps from Section 7 in order.
- Write unit tests inline as an `if __name__ == "__main__":` block in `processing.py` that tests:
  - A normal payload → `state == "NORMAL"`
  - A kick payload (flow 27% above expected) run through anomaly_engine 3 times → `"KICK_RISK"`
  - A payload with missing flow field → `state == "SENSOR_FAULT"`
- Run `python backend/processing.py` and verify all three tests pass and print PASS.

**[PAUSE FOR USER TEST]**
Output: "STEP 3 COMPLETE — Please run: python backend/processing.py Verify all 3 inline tests print PASS. Confirm before I continue."

### STEP 4 — Full WebSocket Ingest + DB Write + Broadcast
Actions:
- In `backend/routers/websocket.py`, implement the full `/ws/ingest` handler:
  - On connect: create a new AnomalyEngine instance for this connection.
  - On message: parse JSON → call `process_payload()` → write to telemetry DB table via asyncpg → broadcast processed state to all `/ws/live` clients.
  - On disconnect: clean up AnomalyEngine instance.
  - On parse error: send back `{"error": "invalid_payload"}` and continue.
- Implement the `/ws/live` handler:
  - On connect: add websocket to a module-level broadcast set.
  - Keep alive with a loop awaiting `websocket.receive_text()`.
  - On disconnect: remove from broadcast set.
- Implement the broadcast helper function: iterate the `/ws/live` set, send the processed state JSON to each, catch and remove dead connections silently.
- Run the mock generator. Verify via server logs that:
  - Payloads are received.
  - Processing runs and produces a processed state.
  - DB write succeeds (check with: `docker exec -it <db_container> psql -U riglab_user -d riglab -c "SELECT COUNT(*) FROM telemetry;"`)

**[PAUSE FOR USER TEST]**
Output: "STEP 4 COMPLETE — Please verify: (1) mock generator is running, (2) server log shows processing output, (3) DB has growing row count. Run: docker exec -it riglab-ai-db-1 psql -U riglab_user -d riglab -c 'SELECT COUNT(*) FROM telemetry;' Confirm before I continue."

### STEP 5 — REST API Endpoints
Actions:
- Implement all REST endpoints from Section 6.2 in their respective router files:
  - `backend/routers/history.py`: GET /telemetry/recent, GET /telemetry/session, GET /sessions
  - `backend/routers/config.py`: GET /config, POST /config (must update the in-memory PETE constants cache as well as the DB row)
  - `backend/routers/reports.py`: POST /reports/incident, POST /reports/daily (for now, these can return a minimal 1-page PDF with ReportLab; full formatting can be improved later)
- All DB queries must use the asyncpg pool from `database.py`.
- Test each endpoint manually:
  - `GET /api/v1/telemetry/recent?limit=10` → returns records
  - `GET /api/v1/config` → returns current constants
  - `POST /api/v1/config` with `{"flow_baseline": 12.0}` → returns updated config
  - `GET /api/v1/config` again → confirms new value persisted
  - `POST /api/v1/reports/incident` → downloads a PDF file

**[PAUSE FOR USER TEST]**
Output: "STEP 5 COMPLETE — Please test all REST endpoints listed above. Confirm each returns the expected response before I continue."

### STEP 6 — Frontend Scaffold & WebSocket Connection
Actions:
- Scaffold the React app: `npm create vite@latest frontend -- --template react` inside the existing `frontend/` directory (merge, do not replace).
- Install dependencies: `npm install recharts`
- Create `vite.config.js` with a proxy rule: `proxy /ws → ws://localhost:8000` (so frontend WS calls work without CORS issues)
- Implement `frontend/src/api/socket.js` exactly as specified in Section 9.3.
- Implement `frontend/src/components/ConnectionStatus.jsx`.
- In `App.jsx`: connect the socket on mount, display ConnectionStatus.
- Run `npm run dev`. Open `http://localhost:5173`.
- Verify ConnectionStatus shows "LIVE" when mock generator is running.
- Verify raw WebSocket messages appear in browser console (add `console.log` in socket.js).

**[PAUSE FOR USER TEST]**
Output: "STEP 6 COMPLETE — Please verify: (1) npm run dev starts without errors, (2) browser shows ConnectionStatus as LIVE, (3) console shows incoming JSON messages. Confirm before I continue."

### STEP 7 — Frontend Components
Actions:
- Implement `frontend/src/App.jsx` with the rolling 60-record buffer from Section 9.4.
- Implement `StateBadge.jsx` per Section 9.2. All colour states must be visible.
- Implement `FlowChart.jsx` per Section 9.2 with both actual and expected flow lines.
- Implement `PressureChart.jsx` per Section 9.2 with P1, P2, and ΔP lines.
- Implement `AngleChart.jsx` per Section 9.2.
- Implement `DataTable.jsx` per Section 9.2 with row colour coding.
- Compose all components into `App.jsx` using the layout from Section 9.1.
- Apply styling in `frontend/src/styles/app.css`:
  - Dark header bar (match RigLab brand: #1F3864 background, white text)
  - Clean white/light-grey card backgrounds for chart panels
  - State badge must be visually dominant
- Run the mock generator with `--scenario cycle`.
- Watch the dashboard cycle through NORMAL → KICK_RISK → LOSS_RISK. All three states must render correctly.

**[PAUSE FOR USER TEST]**
Output: "STEP 7 COMPLETE — Please run: python mock/generator.py --scenario cycle Watch the dashboard for 2–3 minutes. Verify: (1) state badge changes colour and text, (2) all three charts update in real time, (3) data table shows newest records at top. Confirm before I continue."

### STEP 8 — Hardening & Final Integration
Actions:
- Test the camera_fault scenario: `python mock/generator.py --scenario camera_fault`. Verify StateBadge shows SENSOR_FAULT and sensor_status column in DataTable shows CAMERA_FAULT.
- Test config update: `POST /api/v1/config {"flow_baseline": 15.0}` while generator is running. Verify expected_flow values in the DataTable change immediately on next sample. `POST /api/v1/config {"flow_baseline": 10.0}` to restore.
- Test reconnect: kill the mock generator. Verify ConnectionStatus shows DISCONNECTED. Restart the generator. Verify it reconnects and LiveStatus returns to LIVE.
- Test frontend reconnect: stop and restart the Vite dev server. Verify the frontend reconnects to the backend automatically within 10 seconds.
- Verify the drift scenario shows a gradual state change: `python mock/generator.py --scenario drift`. The state must NOT flip on the first breaching sample. It must flip after 3 consecutive.
- Test PDF report generation: `POST /api/v1/reports/daily`. Open the downloaded PDF. Verify it is a readable PDF with at least: title, generation timestamp, record count, and a summary of state counts (how many NORMAL/KICK_RISK/LOSS_RISK records).
- Write a `README.md` in the project root with:
  - Prerequisites (Docker, Python 3.11+, Node 18+)
  - Exact commands to start the system
  - Exact commands to run each mock scenario
  - How to run the test suite in `processing.py`

**[PAUSE FOR USER TEST]**
Output: "STEP 8 COMPLETE — Full system integration verified. Please run through all 7 verification checks in Step 8 and confirm each passes. Once confirmed, the laptop phase of RigLab-AI is complete and ready for the Pi integration phase."

---

## 13. RASPBERRY PI INTEGRATION (DEFERRED — DO NOT IMPLEMENT NOW)

This section documents what will change when real hardware is introduced.
The agent must NOT implement anything in this section during the laptop phase.
It is recorded here so the transition is well-defined.

What stays exactly the same:
- The entire backend (all 9 processing steps, all endpoints, all DB writes)
- The entire frontend
- The mock generator (kept for offline testing and demo fallback)

What changes in the Pi phase:
- A new script runs on the Raspberry Pi: `pi/edge_client.py`
- It reads real pressure and flow sensors via GPIO.
- It runs the OpenCV Hough Line pipeline on the IMX500 camera.
- It assembles a payload matching Section 5.1 schema exactly.
- It sends the payload to `ws://<laptop_ip>:8000/ws/ingest` over Ethernet.
- The laptop IP is set to a static address on the Ethernet interface.
- The GPIO button interrupt handler on the Pi is what starts the `edge_client.py` loop.

No changes to the backend, frontend, or docker-compose are required.
This clean separation is the primary reason the mock generator was designed to produce
the exact same schema as the real Pi. The backend cannot and should not tell the difference.

---

## 14. COMPLETION CRITERIA

The laptop phase is complete when all of the following are true:

- [ ] docker-compose up starts DB and backend with no errors
- [ ] GET /api/v1/health returns db_connected: true
- [ ] Mock generator connects and sends data with all 5 scenarios working
- [ ] All 3 processing unit tests in processing.py pass
- [ ] Telemetry records accumulate in the DB during mock generator runs
- [ ] All REST endpoints return correct responses
- [ ] Frontend connects via WebSocket and shows LIVE status
- [ ] StateBadge shows correct colour and text for all 4 states
- [ ] All 3 charts update in real time
- [ ] DataTable shows last 20 records with row colour coding
- [ ] State does NOT flip on a single breach (anomaly_window enforced)
- [ ] Config update via POST /api/v1/config takes effect on next sample without restart
- [ ] PDF report downloads successfully and is readable
- [ ] Frontend and generator both reconnect automatically after disconnect
- [ ] README.md contains complete startup instructions