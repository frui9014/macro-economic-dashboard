from __future__ import annotations

from typing import Any


def detect_macro_states(dimensions: list[dict[str, Any]], indicator_scores: list[dict[str, Any]], divergences: list[dict[str, Any]]) -> list[str]:
    dm = {item["dimension_id"]: item for item in dimensions}
    im = {item["indicator_id"]: item for item in indicator_scores}

    def score(dimension_id: str) -> float:
        value = dm.get(dimension_id, {}).get("score")
        return value if value is not None else 0.0

    def indicator(indicator_id: str) -> float:
        value = im.get(indicator_id, {}).get("indicator_score")
        return value if value is not None else 0.0

    states: list[str] = []
    if score("china_production") >= 0.5 and score("china_domestic_demand") >= 0.5 and score("credit_expansion") >= 0.3 and score("price_pressure") >= 0.3 and score("real_estate_cycle") >= 0:
        states.append("真复苏")
    if score("china_production") >= 0.5 and score("china_domestic_demand") <= -0.3:
        states.append("供给强、需求弱")
    if score("credit_expansion") >= 0.3 and score("china_domestic_demand") <= 0 and score("real_estate_cycle") <= 0 and indicator("china_fai_infrastructure") > 0:
        states.append("政策托底型增长")
    if score("credit_expansion") >= 0.5 and (score("china_domestic_demand") <= -0.3 or score("real_estate_cycle") <= -0.3):
        states.append("信用传导不畅")
    if score("real_estate_cycle") <= -0.5:
        states.append("地产拖累")
    if score("price_pressure") <= -0.5 and (indicator("china_cpi") < 0 or indicator("china_ppi") < 0):
        states.append("通缩压力")
    if score("external_financial_pressure") <= -0.5:
        states.append("外部逆风")
    if score("global_demand") >= 0.5 and indicator("china_exports") >= 0:
        states.append("外需顺风")
    if score("innovation_upgrade") >= 0.5:
        states.append("创新升级增强")
    neutral = sum(1 for item in dimensions if item.get("score") is None or -0.3 < item["score"] < 0.3)
    low_confidence = sum(1 for item in dimensions if item.get("confidence") == "低")
    if not states or neutral >= 5 or low_confidence >= 4 or len(divergences) >= 4:
        states.append("数据分化、暂难判断")
    return list(dict.fromkeys(states))[:3]
