import importlib.util
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
