"""asyncpg pool setup, schema initialization, and lightweight migrations."""
from __future__ import annotations

import asyncpg

from utils.config import (
    DATABASE_URL,
    PETE_KEYS,
    SYSTEM_SETTING_KEYS,
    set_pete_constant,
    set_system_setting,
)

pool: asyncpg.Pool | None = None


CREATE_TELEMETRY = """
CREATE TABLE IF NOT EXISTS telemetry (
    id                        BIGSERIAL,
    timestamp                 TIMESTAMPTZ NOT NULL,
    pressure1                 FLOAT NOT NULL,
    pressure2                 FLOAT NOT NULL,
    flow                      FLOAT NOT NULL,
    gate_angle                FLOAT,
    pressure_diff             FLOAT NOT NULL,
    expected_flow             FLOAT NOT NULL,
    flow_deviation            FLOAT NOT NULL,
    mud_weight                FLOAT,
    normal_mud_weight         FLOAT,
    mud_weight_with_cuttings  FLOAT,
    viscosity                 FLOAT,
    display_mud_weight        VARCHAR(16) NOT NULL DEFAULT 'normal',
    angle_deviation           FLOAT,
    mud_weight_deviation_pct  FLOAT,
    baseline_angle            FLOAT,
    baseline_mud_weight       FLOAT,
    state                     VARCHAR(12) NOT NULL,
    decision_conf             FLOAT NOT NULL,
    sensor_status             VARCHAR(20) NOT NULL,
    detection_mode            VARCHAR(32) NOT NULL DEFAULT 'angle_only',
    processed_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_health             JSONB NOT NULL
);
"""

CREATE_HYPERTABLE = "SELECT create_hypertable('telemetry', 'timestamp', if_not_exists => TRUE);"

TELEMETRY_MIGRATIONS = (
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'density'
        ) AND NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'mud_weight'
        ) THEN
            ALTER TABLE telemetry RENAME COLUMN density TO mud_weight;
        END IF;
    END
    $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'density_deviation_pct'
        ) AND NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'mud_weight_deviation_pct'
        ) THEN
            ALTER TABLE telemetry RENAME COLUMN density_deviation_pct TO mud_weight_deviation_pct;
        END IF;
    END
    $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'baseline_density'
        ) AND NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'telemetry' AND column_name = 'baseline_mud_weight'
        ) THEN
            ALTER TABLE telemetry RENAME COLUMN baseline_density TO baseline_mud_weight;
        END IF;
    END
    $$;
    """,
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS mud_weight FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS normal_mud_weight FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS mud_weight_with_cuttings FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS viscosity FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS display_mud_weight VARCHAR(16) NOT NULL DEFAULT 'normal'",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS angle_deviation FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS mud_weight_deviation_pct FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS baseline_angle FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS baseline_mud_weight FLOAT",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS detection_mode VARCHAR(32) NOT NULL DEFAULT 'angle_only'",
    "ALTER TABLE telemetry ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
)

CREATE_PETE = """
CREATE TABLE IF NOT EXISTS pete_constants (
    key        VARCHAR(64) PRIMARY KEY,
    value      FLOAT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

INSERT_PETE_DEFAULTS = """
INSERT INTO pete_constants (key, value) VALUES
    ('flow_baseline', 10.0),
    ('anomaly_threshold', 0.15),
    ('anomaly_window', 2),
    ('delta_h_ft', 1.0),
    ('cuttings_density', 21.0),
    ('cuttings_volume_fraction', 0.0),
    ('suspension_factor', 1.0)
ON CONFLICT (key) DO NOTHING;
"""

CREATE_SYSTEM_SETTINGS = """
CREATE TABLE IF NOT EXISTS system_settings (
    key        VARCHAR(64) PRIMARY KEY,
    value      VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

INSERT_SYSTEM_DEFAULTS = """
INSERT INTO system_settings (key, value) VALUES
    ('display_mud_weight', 'normal')
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
        for statement in TELEMETRY_MIGRATIONS:
            await conn.execute(statement)
        await conn.execute(CREATE_HYPERTABLE)
        await conn.execute(CREATE_PETE)
        await conn.execute(INSERT_PETE_DEFAULTS)
        await conn.execute(CREATE_SYSTEM_SETTINGS)
        await conn.execute(INSERT_SYSTEM_DEFAULTS)
        await conn.execute(CREATE_SESSIONS)

        rows = await conn.fetch("SELECT key, value FROM pete_constants")
        for row in rows:
            if row["key"] in PETE_KEYS:
                set_pete_constant(row["key"], row["value"])

        settings = await conn.fetch("SELECT key, value FROM system_settings")
        for row in settings:
            if row["key"] in SYSTEM_SETTING_KEYS:
                set_system_setting(row["key"], row["value"])

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
