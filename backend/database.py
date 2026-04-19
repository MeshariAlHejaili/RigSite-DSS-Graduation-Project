"""asyncpg pool setup and table initialization."""
from __future__ import annotations

import asyncpg

from config import DATABASE_URL, PETE_KEYS, set_pete_constant

pool: asyncpg.Pool | None = None


CREATE_TELEMETRY = """
CREATE TABLE IF NOT EXISTS telemetry (
    id               BIGSERIAL,
    timestamp        TIMESTAMPTZ NOT NULL,
    pressure1        FLOAT NOT NULL,
    pressure2        FLOAT NOT NULL,
    flow             FLOAT NOT NULL,
    gate_angle       FLOAT,
    pressure_diff    FLOAT NOT NULL,
    expected_flow    FLOAT NOT NULL,
    flow_deviation   FLOAT NOT NULL,
    state            VARCHAR(12) NOT NULL,
    decision_conf    FLOAT NOT NULL,
    sensor_status    VARCHAR(20) NOT NULL,
    device_health    JSONB NOT NULL
);
"""

CREATE_HYPERTABLE = "SELECT create_hypertable('telemetry', 'timestamp', if_not_exists => TRUE);"

CREATE_PETE = """
CREATE TABLE IF NOT EXISTS pete_constants (
    key   VARCHAR(64) PRIMARY KEY,
    value FLOAT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

INSERT_PETE_DEFAULTS = """
INSERT INTO pete_constants (key, value) VALUES
    ('flow_baseline', 10.0),
    ('anomaly_threshold', 0.15),
    ('anomaly_window', 2)
ON CONFLICT (key) DO NOTHING;
"""

CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id         BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at   TIMESTAMPTZ,
    note       TEXT
);
"""


async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TELEMETRY)
        await conn.execute(CREATE_HYPERTABLE)
        await conn.execute(CREATE_PETE)
        await conn.execute(INSERT_PETE_DEFAULTS)
        await conn.execute(CREATE_SESSIONS)

        rows = await conn.fetch("SELECT key, value FROM pete_constants")
        for row in rows:
            if row["key"] in PETE_KEYS:
                set_pete_constant(row["key"], row["value"])

        await conn.execute(
            "UPDATE pete_constants SET value = 2, updated_at = NOW() WHERE key = 'anomaly_window' AND value <> 2"
        )
        current_window = await conn.fetchval("SELECT value FROM pete_constants WHERE key = 'anomaly_window'")
        if current_window is not None:
            set_pete_constant("anomaly_window", current_window)


async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


async def is_connected() -> bool:
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return pool
