from __future__ import annotations

from typing import Any


def detect_macro_states(dimensions: list[dict[str, Any]], indicator_scores: list[dict[str, Any]], divergences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dm = {item["dimension_id"]: item for item in dimensions}
    im = {item["indicator_id"]: item for item in indicator_scores}
    found: list[dict[str, Any]] = []

    def score(dimension_id: str) -> float:
        value = dm.get(dimension_id, {}).get("score")
        return value if value is not None else 0.0

    def eligible(*dimension_ids: str) -> bool:
        return all(dm.get(item, {}).get("can_be_macro_state") is True for item in dimension_ids)

    def indicator(indicator_id: str) -> float | None:
        item = im.get(indicator_id, {})
        return item.get("indicator_score") if item.get("status") == "current" else None

    def add(state_id: str, state_name: str, *dimension_ids: str) -> None:
        confidence = min((dm[item]["confidence"] for item in dimension_ids), key={"低": 0, "中": 1, "高": 2}.get) if dimension_ids else "中"
        found.append({
            "state_id": state_id,
            "state_name": state_name,
            "supporting_dimensions": list(dimension_ids),
            "evidence_quality": "strong" if confidence == "高" else "medium" if confidence == "中" else "weak",
            "can_be_macro_state": confidence in {"中", "高"},
        })

    if eligible("china_production", "china_domestic_demand", "credit_expansion", "price_pressure", "real_estate_cycle") and score("china_production") >= 0.5 and score("china_domestic_demand") >= 0.5 and score("credit_expansion") >= 0.3 and score("price_pressure") >= 0.3 and score("real_estate_cycle") >= 0:
        add("true_recovery", "真复苏", "china_production", "china_domestic_demand", "credit_expansion", "price_pressure", "real_estate_cycle")
    if eligible("china_production", "china_domestic_demand") and score("china_production") >= 0.5 and score("china_domestic_demand") <= -0.3:
        add("supply_strong_demand_weak", "供给强、需求弱", "china_production", "china_domestic_demand")
    infrastructure = indicator("china_fai_infrastructure")
    if eligible("credit_expansion", "china_domestic_demand", "real_estate_cycle") and infrastructure is not None and score("credit_expansion") >= 0.3 and score("china_domestic_demand") <= 0 and score("real_estate_cycle") <= 0 and infrastructure > 0:
        add("policy_supported_growth", "政策托底型增长", "credit_expansion", "china_domestic_demand", "real_estate_cycle")
    if eligible("credit_expansion", "china_domestic_demand", "real_estate_cycle") and score("credit_expansion") >= 0.5 and (score("china_domestic_demand") <= -0.3 or score("real_estate_cycle") <= -0.3):
        add("weak_credit_transmission", "信用传导不畅", "credit_expansion", "china_domestic_demand", "real_estate_cycle")
    if eligible("real_estate_cycle") and score("real_estate_cycle") <= -0.5:
        add("real_estate_drag", "地产拖累", "real_estate_cycle")
    if eligible("price_pressure") and score("price_pressure") <= -0.5 and any((indicator(item) or 0) < 0 for item in ("china_cpi", "china_ppi")):
        add("deflation_pressure", "通缩压力", "price_pressure")
    if eligible("external_financial_pressure") and score("external_financial_pressure") <= -0.5:
        add("external_headwind", "外部逆风", "external_financial_pressure")
    exports = indicator("china_exports")
    if eligible("global_demand") and exports is not None and score("global_demand") >= 0.5 and exports >= 0:
        add("external_demand_tailwind", "外需顺风", "global_demand")
    if eligible("innovation_upgrade") and dm["innovation_upgrade"].get("can_enter_summary") and score("innovation_upgrade") >= 0.5:
        add("innovation_upgrade", "创新升级增强", "innovation_upgrade")

    neutral = sum(1 for item in dimensions if item.get("score") is None or -0.3 < item["score"] < 0.3)
    low_confidence = sum(1 for item in dimensions if item.get("confidence") == "低")
    valid_divergences = sum(1 for item in divergences if item.get("can_enter_summary"))
    if not found or neutral >= 5 or low_confidence >= 4 or valid_divergences >= 4:
        found.append({"state_id": "mixed_data", "state_name": "数据分化、暂难判断", "supporting_dimensions": [], "evidence_quality": "medium", "can_be_macro_state": True})
    unique = {item["state_id"]: item for item in found}
    return list(unique.values())[:3]
