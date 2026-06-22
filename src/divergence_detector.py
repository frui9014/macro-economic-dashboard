from __future__ import annotations

from typing import Any


def detect_divergences(dimensions: list[dict[str, Any]], indicator_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dm = {item["dimension_id"]: item for item in dimensions}
    im = {item["indicator_id"]: item for item in indicator_scores}
    found: list[dict[str, Any]] = []

    def score(dimension_id: str) -> float:
        return dm.get(dimension_id, {}).get("score") if dm.get(dimension_id, {}).get("score") is not None else 0.0

    def indicator(indicator_id: str) -> float:
        value = im.get(indicator_id, {}).get("indicator_score")
        return value if value is not None else 0.0

    def add(divergence_id: str, title: str, left: str, right: str, interpretation: str, watch: list[str]) -> None:
        dimension_ids = list(dict.fromkeys(item for item in (left, right) if item in dm))
        confidences = [dm[item].get("confidence", "低") for item in dimension_ids]
        qualified = bool(confidences and all(value in {"中", "高"} for value in confidences) and all(dm[item].get("can_be_macro_state") for item in dimension_ids))
        evidence_quality = "strong" if qualified and all(value == "高" for value in confidences) else "medium" if qualified else "weak"
        found.append({
            "divergence_id": divergence_id,
            "title": title if qualified else f"潜在背离：{title}",
            "status": "confirmed" if qualified else "potential",
            "severity": "高" if evidence_quality == "strong" else "中" if evidence_quality == "medium" else "低",
            "evidence_quality": evidence_quality,
            "can_enter_summary": qualified,
            "evidence": [dm[item]["label"] for item in dimension_ids],
            "interpretation": interpretation,
            "what_to_watch_next": watch,
        })

    if score("china_production") >= 0.5 and score("china_domestic_demand") <= -0.3:
        add("production_strong_demand_weak", "生产强，内需弱", "china_production", "china_domestic_demand", "生产端较强，但消费、进口和就业所代表的内需偏弱，可能呈现供给强、需求弱。", ["社会消费品零售", "进口", "就业"])
    if score("credit_expansion") >= 0.5 and score("china_domestic_demand") <= -0.3:
        add("credit_strong_demand_weak", "信用改善但内需仍弱", "credit_expansion", "china_domestic_demand", "信用扩张尚未有效传导到居民消费和真实需求。", ["居民中长期贷款", "消费", "企业中长期贷款"])
    if score("credit_expansion") >= 0.5 and score("real_estate_cycle") <= -0.3:
        add("credit_strong_real_estate_weak", "信用改善但地产仍弱", "credit_expansion", "real_estate_cycle", "信用可能更多流向政府、基建或企业，居民资产负债表与地产链仍未修复。", ["居民中长期贷款", "商品房销售", "开发投资"])
    if score("china_production") >= 0.5 and score("price_pressure") <= -0.3:
        add("production_strong_price_weak", "生产强，价格弱", "china_production", "price_pressure", "生产有支撑但价格没有修复，呈现量强价弱，企业利润可能承压。", ["PPI", "工业利润", "产能利用率"])
    if indicator("china_exports") >= 0.5 and indicator("china_imports") <= -0.3:
        add("exports_strong_imports_weak", "出口强，进口弱", "global_demand", "china_domestic_demand", "外需或出口竞争力较强，但内需和生产进口需求不足。", ["出口数量与价格", "进口", "制造业新订单"])
    if score("global_demand") <= -0.3 and indicator("china_exports") >= 0.5:
        add("global_demand_weak_exports_strong", "全球需求弱，中国出口强", "global_demand", "china_production", "可能反映中国出口份额、价格优势或特定产业较强。", ["CPB全球贸易", "出口份额", "高技术产品出口"])
    if indicator("us10y") == 1 and indicator("vix") == -1:
        add("yield_down_vix_up", "美债下行但 VIX 上行", "external_financial_pressure", "external_financial_pressure", "收益率下行可能是避险或衰退交易，而非单纯宽松交易。", ["美国就业", "信用利差", "VIX"])

    asset_values = [indicator("csi300"), indicator("hsi")]
    asset_score = sum(asset_values) / len(asset_values)
    if score("external_financial_pressure") <= -0.5 and asset_score >= 0.5:
        add("external_headwind_assets_strong", "外部逆风但中国资产强", "external_financial_pressure", "china_production", "中国资产可能受到政策预期或内部因素支撑，但外部压力仍需警惕。", ["人民币汇率", "政策信号", "北向与南向资金"])
    if asset_score >= 0.5 and score("china_domestic_demand") <= -0.3 and score("real_estate_cycle") <= -0.3:
        add("assets_strong_fundamentals_weak", "股市强但基本面弱", "china_domestic_demand", "real_estate_cycle", "市场上涨可能更多来自政策预期、流动性或风险偏好，而非基本面全面改善。", ["消费", "地产销售", "信用结构"])
    if max(indicator("china_hightech_investment"), indicator("china_rd")) >= 0.5 and indicator("china_hightech_exports") <= -0.3:
        add("innovation_input_strong_exports_weak", "创新投入强，但高技术出口弱", "innovation_upgrade", "global_demand", "产业投入较强，但国际竞争力转化仍需验证。", ["高技术出口占比", "PCT专利", "高技术制造业产出"])
    return found[:5]
