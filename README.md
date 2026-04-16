# RigLab-AI - Laptop Phase

## Prerequisites
- Docker Desktop
- Python 3.11+

## RigLab-AI Docker Stack

This project now uses its own isolated Compose stack so it can live alongside the earlier Claude stack without port collisions.

### Host Ports
- Frontend: `http://localhost:15173`
- Backend API: `http://localhost:18000`
- PostgreSQL/TimescaleDB: `localhost:55432`

### Start the Full Stack
```bash
docker compose up -d --build
```

### Stop the Stack
```bash
docker compose down
```

### View Logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

## Simulate Sensor Traffic

The mock generator reads `MOCK_INGEST_URL` from `.env`, so it targets the dockerized backend by default.

### One payload per second
```bash
python mock/generator.py --scenario normal
```

### Multiple payloads inside the same second
This example sends 4 payloads during each 1-second window.

```bash
python mock/generator.py --scenario normal --interval 1.0 --samples-per-interval 4
```

### Other scenarios
```bash
python mock/generator.py --scenario kick
python mock/generator.py --scenario loss
python mock/generator.py --scenario drift
python mock/generator.py --scenario camera_fault
python mock/generator.py --scenario cycle --interval 1.0 --samples-per-interval 3
```

## Processing Tests

```bash
python backend/processing.py
```

Expected output:

```text
PASS normal -> NORMAL
PASS kick x3 -> KICK_RISK
PASS missing flow -> SENSOR_FAULT
```

## Useful Endpoints
- `GET http://localhost:18000/api/v1/health`
- `GET http://localhost:18000/api/v1/telemetry/recent?limit=50`
- `GET http://localhost:18000/api/v1/sessions`
- `GET http://localhost:18000/api/v1/config`
- `POST http://localhost:18000/api/v1/config`
- `POST http://localhost:18000/api/v1/reports/incident`
- `POST http://localhost:18000/api/v1/reports/daily`
