import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "update_dashboard.py"
WEB_ROOT = Path(__file__).resolve().parents[1] / "src" / "web"
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

    def test_analysis_has_eight_dimensions_and_seven_relations(self):
        indicators = [
            {"id": "us10y", "name": "美国10年期", "frequency": "daily", "status": "ok", "age_days": 0, "five_change": -8, "twenty_change": -10, "date": "2026-06-23", "value": 4.1},
            {"id": "dxy", "name": "美元指数", "frequency": "daily", "status": "ok", "age_days": 0, "five_change": -1, "twenty_change": -2, "date": "2026-06-23", "value": 98},
            {"id": "vix", "name": "VIX", "frequency": "daily", "status": "ok", "age_days": 0, "five_change": -8, "twenty_change": -10, "date": "2026-06-23", "value": 15},
        ]
        payload, judgement = MODULE.build_analysis_payload(indicators, [], datetime(2026, 6, 23, tzinfo=MODULE.BEIJING))
        self.assertEqual(len(payload["dimension_scores"]), 8)
        self.assertEqual(len(payload["relation_diagnostics"]), 7)
        self.assertFalse(judgement["gpt_enabled"])

    def test_analysis_missing_is_not_scored_as_zero(self):
        scores = MODULE.score_indicators([{"id": "x", "name": "缺失", "frequency": "monthly", "status": "failed", "age_days": None}])
        self.assertIsNone(scores[0]["indicator_score"])
        self.assertEqual(scores[0]["status"], "stale")

    def test_optional_gpt_falls_back_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = MODULE.generate_gpt_judgement({"dimension_scores": [], "candidate_macro_states": []}, MODULE.PROMPTS_ROOT)
        self.assertFalse(result["gpt_enabled"])
        self.assertEqual(result["gpt_status"], "not_configured")


class DashboardFrontendContractTest(unittest.TestCase):
    def test_trend_frequency_and_period_controls_exist(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        for control_id in ("frequency-filter", "indicator-select", "range-switch", "start-control", "end-control"):
            self.assertIn(f'id="{control_id}"', html)
        for frequency in ("all", "daily", "monthly", "quarterly", "annual"):
            self.assertIn(f'value="{frequency}"', html)

    def test_confidence_is_not_rendered(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        legacy_dimension_renderer = app.split("function renderDimensions()", 1)[1].split("function renderIndicators()", 1)[0]
        self.assertNotIn("item.confidence", legacy_dimension_renderer)

    def test_frequency_specific_presets_and_axis_are_present(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        for marker in ("RANGE_PRESETS", "daily:", "monthly:", "quarterly:", "annual:", "axisLabel", "periodKey"):
            self.assertIn(marker, app)

    def test_analysis_tab_and_contract_exist(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-tab="analysis"', html)
        for target in ("analysis-dimensions", "analysis-relations", "analysis-divergences", "analysis-quality"):
            self.assertIn(f'id="{target}"', html)
        self.assertIn("function renderAnalysis()", app)


if __name__ == "__main__":
    unittest.main()
