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

    def test_daily_macro_payload_is_minimal_for_gpt(self):
        analysis_payload, _ = MODULE.build_analysis_payload([], [], datetime(2026, 6, 23, tzinfo=MODULE.BEIJING))
        self.assertIn("indicator_scores", analysis_payload)
        self.assertIn("data_freshness", analysis_payload)
        payload = MODULE.build_gpt_payload(analysis_payload)
        self.assertEqual(
            set(payload),
            {
                "date",
                "dimension_scores",
                "relation_diagnostics",
                "detected_divergences",
                "candidate_macro_states",
                "important_data_updates",
                "missing_or_stale_data",
            },
        )
        for removed_key in ("indicator_scores", "raw_key_values_summary", "data_freshness", "generated_at", "purpose", "rule_summary"):
            self.assertNotIn(removed_key, payload)

    def test_analysis_missing_is_not_scored_as_zero(self):
        scores = MODULE.score_indicators([{"id": "x", "name": "缺失", "frequency": "monthly", "status": "failed", "age_days": None}])
        self.assertIsNone(scores[0]["indicator_score"])
        self.assertEqual(scores[0]["status"], "stale")

    def test_optional_gpt_falls_back_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = MODULE.generate_gpt_judgement({"dimension_scores": [], "candidate_macro_states": []}, MODULE.PROMPTS_ROOT)
        self.assertFalse(result["gpt_enabled"])
        self.assertEqual(result["gpt_status"], "not_configured")
        self.assertEqual(result["main_judgement"], "未启用 GPT 解读，仅展示规则引擎分析结果。")

    def test_low_confidence_real_estate_cannot_be_macro_state(self):
        history = [{"date": f"2025-{month:02d}", "value": 100 - month} for month in range(1, 13)] + [{"date": "2026-01", "value": 70}]
        indicators = [{"id": "china_property_sales", "name": "商品房销售面积", "frequency": "monthly", "status": "ok", "age_days": 10, "date": "2026-01", "value": 70, "history": history}]
        scores = MODULE.score_indicators(indicators)
        dimensions = MODULE.build_dimension_scores(indicators, scores, datetime(2026, 2, 15))
        estate = next(item for item in dimensions if item["dimension_id"] == "real_estate_cycle")
        states = MODULE.detect_macro_states(dimensions, scores, [])
        self.assertEqual(estate["confidence"], "低")
        self.assertEqual(estate["label"], "地产信号偏弱，但证据不足")
        self.assertNotIn("地产拖累", [item["state_name"] for item in states])

    def test_low_confidence_divergence_is_only_potential(self):
        dimensions = [
            {"dimension_id": "china_production", "label": "生产改善", "score": .8, "confidence": "高", "can_be_macro_state": True},
            {"dimension_id": "china_domestic_demand", "label": "内需偏弱", "score": -.8, "confidence": "低", "can_be_macro_state": False},
        ]
        result = MODULE.detect_divergences(dimensions, [])
        self.assertEqual(result[0]["status"], "potential")
        self.assertNotEqual(result[0]["severity"], "高")
        self.assertFalse(result[0]["can_enter_summary"])

    def test_seasonal_credit_does_not_use_previous_month(self):
        values = [100 + index for index in range(15)]
        item = {"id": "china_tsf", "name": "社融", "frequency": "monthly", "status": "ok", "age_days": 10, "date": "2026-03", "value": values[-1], "previous_value": values[-2], "history": [{"date": str(index), "value": value} for index, value in enumerate(values)]}
        result = MODULE.score_indicators([item])[0]
        self.assertIn("same_period", result["comparison_method"])

    def test_indicator_metadata_distinguishes_release_and_fetch(self):
        now = datetime(2026, 6, 23, 18, 30, tzinfo=MODULE.BEIJING)
        items = [{"id": "x", "date": "2026-05", "value": 2, "frequency": "monthly", "status": "ok"}]
        previous = {"indicators": [{"id": "x", "date": "2026-04", "value": 1, "frequency": "monthly", "fetched_at": "old"}]}
        MODULE.annotate_run_metadata(items, previous, [{"id": "x", "action": "updated", "status": "ok"}], now)
        for field in ("observation_period", "released_at", "fetched_at", "value_changed_since_last_run"):
            self.assertIn(field, items[0])
        self.assertEqual(items[0]["observation_period"], "2026-05")
        self.assertEqual(items[0]["released_at"], "2026-06-23")
        self.assertTrue(items[0]["value_changed_since_last_run"])

    def test_oil_can_contribute_differently_by_dimension(self):
        history = [{"date": str(index), "value": 100 + (index % 2) * .1} for index in range(30)]
        history[-1]["value"] = 120
        item = {"id": "brent", "name": "Brent", "frequency": "daily", "status": "ok", "age_days": 0, "date": "2026-06-23", "value": 120, "five_change": 20, "twenty_change": 20, "history": history}
        result = MODULE.score_indicators([item])[0]["dimension_contributions"]
        self.assertIn("global_demand", result)
        self.assertIn("price_pressure", result)
        self.assertNotEqual(result["global_demand"], result["price_pressure"])

    def test_credit_without_structure_is_not_called_effective(self):
        def flow(indicator_id):
            values = [100 + index * 5 for index in range(15)]
            return {"id": indicator_id, "name": indicator_id, "frequency": "monthly", "status": "ok", "age_days": 5, "date": "2026-03", "value": values[-1], "history": [{"date": str(index), "value": value} for index, value in enumerate(values)]}
        indicators = [flow("china_tsf"), flow("china_new_loans")]
        dimensions = MODULE.build_dimension_scores(indicators, MODULE.score_indicators(indicators), datetime(2026, 4, 1))
        credit = next(item for item in dimensions if item["dimension_id"] == "credit_expansion")
        self.assertFalse(credit["effective_expansion"])
        self.assertIn("结构待验证", credit["label"])


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

    def test_analysis_page_explains_weak_stale_and_missing_evidence(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        for phrase in ("证据不足，不进入主判断", "数据较旧，仅作背景", "数据缺失，未参与打分"):
            self.assertIn(phrase, app)
        self.assertIn("analysis.data_freshness", app)

    def test_frontend_never_calls_openai_api(self):
        for path in (WEB_ROOT / "app.js", WEB_ROOT / "index.html"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("api.openai.com", content)
            self.assertNotIn("OPENAI_API_KEY", content)

    def test_gpt_security_configuration_is_documented(self):
        project_root = WEB_ROOT.parents[1]
        readme = (project_root / "README.md").read_text(encoding="utf-8")
        gitignore = (project_root / ".gitignore").read_text(encoding="utf-8")
        for marker in ("Settings → Secrets and variables → Actions", "OPENAI_API_KEY", "OPENAI_MODEL", "macro_judgement.json"):
            self.assertIn(marker, readme)
        self.assertIn(".env", gitignore)

    def test_prompt_has_evidence_hard_gates(self):
        prompt = (WEB_ROOT.parents[1] / "prompts" / "macro_analysis_system.txt").read_text(encoding="utf-8")
        for marker in ("can_enter_summary=true", "can_be_macro_state=true", "不得把“今天抓到旧数据”"):
            self.assertIn(marker, prompt)


if __name__ == "__main__":
    unittest.main()
