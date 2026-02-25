# RigLab-AI — Drilling Monitoring Prototype

Full-stack app for drilling situation monitoring (Kick/Loss detection) with Excel upload and real-time playback.

## Project structure

```
├── backend/           # Python FastAPI API
│   ├── main.py        # API entry point
│   ├── database.py    # SQLite + SQLAlchemy config
│   ├── models.py      # SQLAlchemy models
│   └── scripts/
│       └── generate_data.py   # Generate test Excel data
├── frontend/          # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── ...
├── requirements.txt
└── README.md
```

## Setup

### Backend (Python)

```bash
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run

**Terminal 1 — backend** (from project root):
```bash
npm run backend
# or: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend**:
```bash
npm run frontend
# or: cd frontend && npm run dev
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173  

## Generate test data

```bash
python -m backend.scripts.generate_data
```

Creates `sensor_data.xlsx` at project root. Upload it via the UI.
