# RigSite-DSS — Development Roadmap

> Scope: graduation project prototype. Items are kept practical and focused.

---

## Phase 1 — Quick Fixes & Foundation (do first)

### 1. Fix Simulator Angle Ranges
- **What:** Constrain simulated gate angles per scenario — normal: 50–55°, kick: 60–85°, loss: 5–40°
- **Why:** Current simulator does not reliably stay in the correct range, making testing and demos unreliable
- **Priority:** High
- **Dependencies:** None
- **Files:** `backend/simulator.py`, `backend/simulator_scenarios.py`

### 2. Reorganize Files into Folders
- **What:** Group backend files into subfolders — `core/` (engine, classifier, detector), `utils/` (config, processing), keep `routers/` as-is
- **Why:** Flat backend structure is hard to navigate as the codebase grows
- **Priority:** High
- **Dependencies:** None (do before adding new features)
- **Files:** All `backend/*.py` modules

---

## Phase 2 — Data Layer

### 3. Restructure the Database
- **What:** Add columns/tables for new calculated variables: viscosity, normal mud weight, mud weight with cuttings, density
- **Why:** Current schema only stores raw sensor values; reports and dashboard cannot show derived variables without schema support
- **Priority:** High
- **Dependencies:** Phase 1 complete (cleaner file layout makes migration easier)
- **Files:** `backend/database.py`, `backend/models.py`

### 4. Add New Calculated Metrics
- **What:** Implement backend calculations for: viscosity, normal mud weight, mud weight with cuttings, density — derived from existing sensor inputs
- **Why:** These are the physically meaningful indicators that operators care about, not raw sensor voltages
- **Priority:** High
- **Dependencies:** Item 3 (DB schema updated)
- **Files:** `backend/engineering.py` (add formulas), `backend/processing.py`

---

## Phase 3 — Dashboard & UI

### 5. Replace Raw Sensor Data with Calculated Variables
- **What:** Show viscosity, mud weights, and density in the dashboard instead of (or alongside) raw pressure/flow readings
- **Why:** Operators interpret mud properties, not raw ADC values
- **Priority:** High
- **Dependencies:** Item 4 (metrics available from backend)
- **Files:** `frontend/src/components/DataTable.jsx`, relevant chart components

### 6. Reformat and Reorganize the Raw Data Table
- **What:** Clean up column order, add units, improve column headers, optionally collapse low-interest columns
- **Why:** Current table is hard to read in the dashboard
- **Priority:** Medium
- **Dependencies:** Item 5 (so final columns are known before reformatting)
- **Files:** `frontend/src/components/DataTable.jsx`

### 7. Remove or Hide Sensor Status Indicators
- **What:** Evaluate whether sensor status badges serve a purpose; if not, remove them; if marginal, put behind a toggle
- **Why:** They add visual noise and may confuse operators if the logic is not accurate
- **Priority:** Medium
- **Dependencies:** Item 5
- **Files:** `frontend/src/components/StateBadge.jsx`, `frontend/src/App.jsx`

### 8. Reorganize UI into Logical Pages / Sections
- **What:** Split the dashboard into at minimum: **Live Monitor**, **History / Raw Data**, **Reports**, **Settings** — use tabs or separate routes
- **Why:** Everything on one page makes the UI crowded and hard to navigate
- **Priority:** Medium
- **Dependencies:** Items 5–7 (so you know what belongs on each page before restructuring)
- **Files:** `frontend/src/App.jsx`, all components

### 9. Add Mud Weight Display Setting
- **What:** Settings toggle to choose which mud weight is shown — normal mud weight or mud weight with cuttings
- **Why:** Different operators / stages of drilling prefer different metrics
- **Priority:** Medium
- **Dependencies:** Item 4 (both metrics computed), Item 8 (Settings page exists)
- **Files:** `frontend/src/components/SettingsPage.jsx`, `backend/routers/config.py`

---

## Phase 4 — Reports & Integration

### 10. Improve Daily and Incident Reports
- **What:** Include new metrics (viscosity, mud weights, density) in report output; add anomaly summary with timestamps and detected mode; improve formatting
- **Why:** Current reports show minimal information and are not useful for post-event review
- **Priority:** Medium
- **Dependencies:** Item 4 (metrics available), Item 3 (DB stores them)
- **Files:** `backend/reports/`, `backend/routers/reports.py`, `frontend/src/components/ReportControls.jsx`

### 11. WebSocket Readiness for Raspberry Pi
- **What:** Ensure the WebSocket endpoint accepts: (a) JSON frames with pressure1, pressure2, flow meter; (b) one gate image per second as binary or base64; validate and handle connection drops gracefully
- **Why:** The system needs to work with the physical hardware setup without code changes
- **Priority:** Medium
- **Dependencies:** Items 3–4 (data pipeline must be ready to process incoming data)
- **Files:** `backend/routers/websocket.py`, `backend/processing.py`

---

## Extra Suggested Items
> Not in the original requirements — add only if time allows.

| # | Item | Why | Priority |
|---|------|-----|----------|
| E1 | Add CSV export for raw data table | Useful for lab analysis and report submission | Low |
| E2 | Add input validation + error feedback for WebSocket frames | Prevents silent data corruption from malformed Pi messages | Low |
| E3 | Add a connection quality indicator for the Raspberry Pi link | Operators need to know if the hardware is live | Low |

---

## Recommended Implementation Order

| Step | Item | Reason |
|------|------|---------|
| 1 | Fix simulator | Isolated, zero dependencies, unblocks testing immediately |
| 2 | Reorganize files | No behavior changes; makes all future work cleaner |
| 3 | Restructure DB | Foundation — everything else depends on schema |
| 4 | Add new metrics (backend) | Needed before any UI or report work |
| 5 | Replace raw data with metrics (frontend) | Core dashboard improvement, unblocks UI decisions |
| 6 | Reformat data table | Now you know the final columns |
| 7 | Remove/hide sensor status | Low risk cleanup after table is settled |
| 8 | Reorganize UI into pages | Do after content is finalized, not before |
| 9 | Mud weight settings toggle | Simple once the Settings page exists |
| 10 | Improve reports | Needs both DB and metrics ready |
| 11 | WebSocket Pi readiness | Do last — validates the full pipeline end-to-end |
