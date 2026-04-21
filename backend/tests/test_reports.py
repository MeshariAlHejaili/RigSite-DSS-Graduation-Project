from __future__ import annotations

import datetime
import sys
import types
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    import reportlab  # type: ignore # noqa: F401
except ModuleNotFoundError:
    fake_reportlab = types.ModuleType("reportlab")
    fake_reportlab.__path__ = []
    fake_reportlab_lib = types.ModuleType("reportlab.lib")
    fake_reportlab_lib.__path__ = []
    fake_reportlab_colors = types.ModuleType("reportlab.lib.colors")
    fake_reportlab_colors.HexColor = lambda value: value
    fake_reportlab_colors.white = "white"
    fake_reportlab_colors.grey = "grey"

    fake_reportlab_pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    fake_reportlab_pagesizes.A4 = (595, 842)

    fake_reportlab_styles = types.ModuleType("reportlab.lib.styles")
    fake_reportlab_styles.getSampleStyleSheet = lambda: {  # noqa: E731
        "Title": object(),
        "Normal": object(),
        "Heading2": object(),
        "Heading3": object(),
    }

    fake_reportlab_platypus = types.ModuleType("reportlab.platypus")

    class _Dummy:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def setStyle(self, *args, **kwargs) -> None:  # noqa: N802
            return None

        def build(self, *args, **kwargs) -> None:
            return None

    fake_reportlab_platypus.Paragraph = _Dummy
    fake_reportlab_platypus.SimpleDocTemplate = _Dummy
    fake_reportlab_platypus.Spacer = _Dummy
    fake_reportlab_platypus.Table = _Dummy
    fake_reportlab_platypus.TableStyle = _Dummy

    sys.modules["reportlab"] = fake_reportlab
    sys.modules["reportlab.lib"] = fake_reportlab_lib
    sys.modules["reportlab.lib.colors"] = fake_reportlab_colors
    sys.modules["reportlab.lib.pagesizes"] = fake_reportlab_pagesizes
    sys.modules["reportlab.lib.styles"] = fake_reportlab_styles
    sys.modules["reportlab.platypus"] = fake_reportlab_platypus

try:
    import asyncpg  # type: ignore # noqa: F401
except ModuleNotFoundError:
    fake_asyncpg = types.ModuleType("asyncpg")

    class _FakePool:
        pass

    async def _fake_create_pool(*args, **kwargs):
        return _FakePool()

    fake_asyncpg.Pool = _FakePool
    fake_asyncpg.create_pool = _fake_create_pool
    sys.modules["asyncpg"] = fake_asyncpg

from reports import generator  # noqa: E402
from routers import reports as reports_router  # noqa: E402


class DailyWindowTests(unittest.TestCase):
    def test_daily_window_uses_local_calendar_day(self) -> None:
        original_timezone = reports_router.REPORT_TIMEZONE
        reports_router.REPORT_TIMEZONE = "Asia/Riyadh"
        try:
            now_utc = datetime.datetime(2026, 4, 21, 21, 30, tzinfo=datetime.timezone.utc)
            day_start_utc, next_day_start_utc, local_date, tz_name = reports_router._daily_window_for_now(now_utc)
        finally:
            reports_router.REPORT_TIMEZONE = original_timezone

        self.assertEqual(tz_name, "Asia/Riyadh")
        self.assertEqual(local_date, datetime.date(2026, 4, 22))
        self.assertEqual(day_start_utc, datetime.datetime(2026, 4, 21, 21, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(next_day_start_utc, datetime.datetime(2026, 4, 22, 21, 0, tzinfo=datetime.timezone.utc))


class DailyStatsTests(unittest.TestCase):
    def test_cuttings_min_max_is_not_specified_when_absent(self) -> None:
        records = [
            {
                "timestamp": "2026-04-21T01:00:00Z",
                "state": "NORMAL",
                "gate_angle": 12.2,
                "viscosity": 3.5,
                "normal_mud_weight": 9.6,
                "mud_weight_with_cuttings": None,
            },
            {
                "timestamp": "2026-04-21T02:00:00Z",
                "state": "KICK_RISK",
                "gate_angle": 14.8,
                "viscosity": 4.1,
                "normal_mud_weight": 10.2,
                "mud_weight_with_cuttings": None,
            },
        ]
        rows = generator._variable_stat_rows(records)
        cuttings_row = next(row for row in rows if row[0] == "Mud Weight w/ Cuttings (ppg)")

        self.assertEqual(cuttings_row[1], "Not specified")
        self.assertEqual(cuttings_row[2], "Not specified")
        self.assertEqual(cuttings_row[3], "0")

    def test_incident_kpis_count_latest_episode_from_day_records(self) -> None:
        records = [
            {"timestamp": "2026-04-21T00:00:00Z", "state": "NORMAL"},
            {"timestamp": "2026-04-21T00:00:01Z", "state": "KICK_RISK"},
            {"timestamp": "2026-04-21T00:00:02Z", "state": "KICK_RISK"},
            {"timestamp": "2026-04-21T00:00:03Z", "state": "NORMAL"},
            {"timestamp": "2026-04-21T00:00:04Z", "state": "LOSS_RISK"},
            {"timestamp": "2026-04-21T00:00:05Z", "state": "KICK_RISK"},
        ]
        rows = generator._incident_kpi_rows(records, "UTC")
        as_dict = {row[0]: row[1] for row in rows[1:]}

        self.assertEqual(as_dict["Kick episodes"], "2")
        self.assertEqual(as_dict["Loss episodes"], "1")
        self.assertEqual(as_dict["Risky-record %"], "66.67%")
        self.assertIn("2026-04-21 00:00:05 UTC", as_dict["Latest incident time"])


class IncidentSummaryTests(unittest.TestCase):
    def test_mixed_episode_type(self) -> None:
        records = [
            {"timestamp": "2026-04-21T11:00:00Z", "state": "KICK_RISK"},
            {"timestamp": "2026-04-21T11:00:02Z", "state": "LOSS_RISK"},
        ]
        self.assertEqual(generator._incident_type(records), "MIXED")

    def test_no_incident_episode_returns_empty(self) -> None:
        records = [
            {"timestamp": "2026-04-21T11:00:00Z", "state": "NORMAL"},
            {"timestamp": "2026-04-21T11:00:02Z", "state": "SENSOR_FAULT"},
        ]
        self.assertEqual(generator._risk_episodes(records), [])


if __name__ == "__main__":
    unittest.main()
