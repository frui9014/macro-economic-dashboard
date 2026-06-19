import importlib.util
from pathlib import Path
import unittest
from datetime import datetime


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "update_dashboard.py"
SPEC = importlib.util.spec_from_file_location("update_dashboard", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DashboardCalculationsTest(unittest.TestCase):
    def test_pct_change(self):
        self.assertAlmostEqual(MODULE.pct_change(110, 100), 10)
        self.assertIsNone(MODULE.pct_change(10, 0))

    def test_indicator_changes(self):
        config = {
            "id": "x",
            "name": "测试指标",
            "unit": "点",
            "decimals": 2,
            "group": "测试",
            "meaning": "测试原因",
            "consequence_up": "上行后果",
            "consequence_down": "下行后果",
            "source": "测试源",
        }
        points = [
            {"date": "2026-01-01", "value": 100},
            {"date": "2026-01-02", "value": 101},
            {"date": "2026-01-03", "value": 102},
        ]
        result = MODULE.build_indicator(config, points, "https://example.com")
        self.assertEqual(result["direction"], "up")
        self.assertAlmostEqual(result["day_change"], 0.9901, places=4)

    def test_dimensions_do_not_claim_missing_macro_data(self):
        dimensions = MODULE.build_dimensions([])
        statuses = {item["name"]: item["status"] for item in dimensions}
        self.assertEqual(statuses["中国内需"], "待宏观数据")
        self.assertEqual(statuses["创新升级"], "待结构数据")

    def test_release_window_scheduler(self):
        item = {"frequency": "monthly", "release_days": [9, 10, 11]}
        previous = {"status": "ok"}
        due, reason = MODULE.should_scan(item, datetime(2026, 6, 10), previous)
        self.assertTrue(due)
        self.assertEqual(reason, "release_window")
        due, reason = MODULE.should_scan(item, datetime(2026, 6, 20), previous)
        self.assertFalse(due)
        self.assertEqual(reason, "outside_release_window")

    def test_first_scan_ignores_release_window(self):
        item = {"frequency": "annual", "release_months": [9]}
        due, reason = MODULE.should_scan(item, datetime(2026, 6, 20), None)
        self.assertTrue(due)
        self.assertEqual(reason, "initial_or_forced")

    def test_same_day_failure_is_not_retried(self):
        item = {"frequency": "monthly", "release_days": [19]}
        failed = {"status": "failed", "last_attempt": "2026-06-19"}
        due, reason = MODULE.should_scan(item, datetime(2026, 6, 19), failed)
        self.assertFalse(due)
        self.assertEqual(reason, "same_day_failure_backoff")

    def test_stale_data_is_excluded_from_signals(self):
        items = [{"id": "x", "status": "ok", "freshness_status": "stale"}]
        self.assertIsNone(MODULE.get_indicator(items, "x"))

    def test_monthly_freshness(self):
        items = [{"id": "x", "date": "2026年05月份", "frequency": "monthly", "status": "ok"}]
        MODULE.annotate_freshness(items, datetime(2026, 6, 19, tzinfo=MODULE.BEIJING))
        self.assertEqual(items[0]["freshness_status"], "current")
        self.assertTrue(items[0]["eligible_for_signal"])


if __name__ == "__main__":
    unittest.main()
