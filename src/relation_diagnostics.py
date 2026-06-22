from __future__ import annotations

from typing import Any


CONFIDENCE_RANK = {"低": 0, "中": 1, "高": 2}


def _state(score: float | None) -> int:
    return 1 if score is not None and score >= 0.5 else -1 if score is not None and score <= -0.5 else 0


def _confidence(*items: dict[str, Any]) -> str:
    if not items:
        return "低"
    return min((item.get("confidence", "低") for item in items), key=lambda value: CONFIDENCE_RANK.get(value, 0))


def _evidence(*items: dict[str, Any]) -> list[str]:
    evidence: list[str] = []
    for item in items:
        evidence.append(f"{item['dimension_name']}：{item['label']}（{item.get('score')}）")
    return evidence


def build_relation_diagnostics(dimensions: list[dict[str, Any]], indicator_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dm = {item["dimension_id"]: item for item in dimensions}
    im = {item["indicator_id"]: item for item in indicator_scores}
    relations: list[dict[str, Any]] = []

    def add(relation_id: str, name: str, conclusion: str, used: list[dict[str, Any]], risk: str) -> None:
        confidence = _confidence(*used)
        relations.append({"relation_id": relation_id, "relation_name": name, "conclusion": conclusion, "evidence": _evidence(*used), "risk_note": risk, "confidence": confidence, "evidence_quality": "strong" if confidence == "高" else "medium" if confidence == "中" else "weak", "can_enter_summary": confidence in {"中", "高"}})

    production, demand = dm["china_production"], dm["china_domestic_demand"]
    pair = (_state(production["score"]), _state(demand["score"]))
    conclusions = {(1, 1): "生产与内需共同改善，接近真复苏", (1, -1): "供给强、需求弱", (-1, 1): "消费托底但生产尚未跟上", (-1, -1): "生产与需求均偏弱"}
    add("production_vs_domestic_demand", "生产 vs 内需", conclusions.get(pair, "生产与内需信号尚未形成明确共振"), [production, demand], "中性区间不等于没有变化，需结合最新月度数据。")

    credit = dm["credit_expansion"]
    pair = (_state(credit["score"]), _state(demand["score"]))
    conclusions = {(1, 1): "信用有效传导到真实需求", (1, -1): "信用传导不畅", (-1, -1): "融资需求不足", (-1, 1): "内需有韧性但金融支持不足"}
    add("credit_vs_domestic_demand", "信用 vs 内需", conclusions.get(pair, "信用与内需结构分化或处于中性区间"), [credit, demand], "社融总量改善不必然代表居民与企业融资需求改善。")

    estate = dm["real_estate_cycle"]
    pair = (_state(credit["score"]), _state(estate["score"]))
    conclusions = {(1, 1): "信用正在传导至地产链条", (1, -1): "信用可能更多流向政府、基建或企业", (-1, -1): "地产与融资需求均弱", (-1, 1): "局部地产修复仍需验证"}
    add("credit_vs_real_estate", "信用 vs 地产", conclusions.get(pair, "信用与地产均未形成明确方向"), [credit, estate], "缺少贷款结构时，不能确认资金最终流向。")

    price = dm["price_pressure"]
    growth_score = None if production["score"] is None or demand["score"] is None else (production["score"] + demand["score"]) / 2
    growth = _state(growth_score)
    pstate = _state(price["score"])
    conclusions = {(1, 1): "增长与价格共同修复，接近健康复苏", (1, -1): "量强价弱，企业利润可能承压", (-1, -1): "增长偏弱并伴随通缩压力", (-1, 1): "成本冲击或滞胀压力"}
    add("growth_vs_price", "增长 vs 价格", conclusions.get((growth, pstate), "增长与价格信号分化"), [production, demand, price], "价格变化需区分需求修复与供给、能源冲击。")

    global_demand = dm["global_demand"]
    exports = im.get("china_exports")
    export_state = _state(exports.get("indicator_score") if exports else None)
    pair = (_state(global_demand["score"]), export_state)
    conclusions = {(1, 1): "全球需求与中国出口共同走强，外需顺风", (-1, -1): "全球需求与中国出口共同走弱", (-1, 1): "中国份额、价格或产业优势可能形成支撑", (1, -1): "中国出口竞争力或结构面临压力"}
    relation_confidence = "低" if not exports or exports.get("indicator_score") is None else global_demand["confidence"]
    relation = {"relation_id": "global_demand_vs_china_exports", "relation_name": "全球需求 vs 中国出口", "conclusion": conclusions.get(pair, "全球需求与中国出口尚未形成明确组合"), "evidence": _evidence(global_demand) + ([f"中国出口单项得分：{exports['indicator_score']}"] if exports else ["中国出口数据缺失"]), "risk_note": "出口还会受到价格、基数和贸易结构影响。", "confidence": relation_confidence, "evidence_quality": "strong" if relation_confidence == "高" else "medium" if relation_confidence == "中" else "weak", "can_enter_summary": relation_confidence in {"中", "高"}}
    relations.append(relation)

    external = dm["external_financial_pressure"]
    asset_scores = [im.get(item_id, {}).get("indicator_score") for item_id in ("csi300", "hsi")]
    asset_scores = [value for value in asset_scores if value is not None]
    asset_state = _state(sum(asset_scores) / len(asset_scores)) if asset_scores else 0
    pair = (_state(external["score"]), asset_state)
    conclusions = {(1, 1): "外部环境支持中国风险资产", (-1, -1): "外部压力与中国资产走弱共振", (-1, 1): "政策预期或中国内部因素可能形成支撑", (1, -1): "中国内部基本面可能仍弱"}
    confidence = "低" if len(asset_scores) < 2 else external["confidence"]
    relations.append({"relation_id": "external_financial_pressure_vs_china_assets", "relation_name": "外部金融压力 vs 中国资产", "conclusion": conclusions.get(pair, "外部条件与中国资产信号分化"), "evidence": _evidence(external) + [f"中国资产合成方向：{asset_state}"], "risk_note": "市场价格反映预期，不能替代基本面数据。", "confidence": confidence, "evidence_quality": "strong" if confidence == "高" else "medium" if confidence == "中" else "weak", "can_enter_summary": confidence in {"中", "高"}})

    innovation = dm["innovation_upgrade"]
    hightech_ids = ("china_hightech_exports", "china_hightech_output", "china_hightech_investment")
    hightech = [im.get(item_id, {}).get("indicator_score") for item_id in hightech_ids]
    hightech = [value for value in hightech if value is not None]
    conversion = _state(sum(hightech) / len(hightech)) if hightech else 0
    pair = (_state(innovation["score"]), conversion)
    conclusions = {(1, 1): "创新投入与产业、出口转化较好", (1, -1): "产业投入较强，但国际转化仍待验证", (-1, 1): "出口可能更多依赖既有制造优势", (-1, -1): "创新升级整体偏弱"}
    confidence = "低" if len(hightech) < 2 else innovation["confidence"]
    relations.append({"relation_id": "innovation_vs_hightech_exports", "relation_name": "创新升级 vs 高技术出口", "conclusion": conclusions.get(pair, "创新投入与转化信号尚不充分"), "evidence": _evidence(innovation) + [f"高技术产业与出口合成方向：{conversion}"], "risk_note": "创新是慢变量，不宜根据单日或单月数据过度解读。", "confidence": confidence, "evidence_quality": "strong" if confidence == "高" else "medium" if confidence == "中" else "weak", "can_enter_summary": confidence in {"中", "高"}})
    return relations
