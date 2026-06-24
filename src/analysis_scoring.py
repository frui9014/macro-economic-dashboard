from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Any


# Analysis validity is about whether the latest official observation is still
# usable for judgement, not whether it was released today.
ANALYSIS_VALIDITY_DAYS = {"daily": 3, "weekly": 21, "monthly": 45, "quarterly": 120, "annual": 450}
HISTORY_REQUIREMENTS = {"daily": 20, "monthly": 12, "quarterly": 8, "annual": 3}

ROLE_WEIGHTS = {"core": 1.0, "secondary": 0.6, "auxiliary": 0.3}
CONFIDENCE_RANK = {"低": 0, "中": 1, "高": 2}

INVERSE_IDS = {"us10y", "us2y", "dxy", "vix", "usdcny", "us_unemployment", "china_unemployment", "china_youth_unemployment"}
DIRECT_COMPARISON_IDS = {
    "china_pmi_man", "china_pmi_nonman", "china_pmi_composite", "us_ism_man", "us_ism_services",
    "china_unemployment", "china_youth_unemployment", "us_unemployment", "china_cpi", "china_ppi",
}
SEASONAL_FLOW_IDS = {"china_tsf", "china_new_loans", "china_gov_bonds", "china_bill_financing", "china_property_sales", "china_property_sales_value", "china_property_starts"}
YOY_RATE_IDS = {
    "china_gdp", "china_industrial", "china_retail", "china_fai", "china_fai_manufacturing",
    "china_fai_infrastructure", "china_fai_property", "china_property_investment", "china_exports",
    "china_imports", "china_m2", "china_hightech_output", "china_hightech_investment", "us_nonfarm",
    "us_cpi", "us_core_cpi", "us_core_pce", "oecd_cli", "global_trade",
}

DAILY_THRESHOLDS = {
    "us10y": 5.0, "us2y": 5.0, "dxy": 0.3, "vix": 5.0, "usdcny": 0.3,
    "csi300": 0.5, "hsi": 0.5, "hscei": 0.5, "china10y": 5.0,
    "brent": 0.8, "wti": 0.8, "copper": 0.6,
}


def member(role: str, *indicator_ids: str) -> dict[str, dict[str, Any]]:
    return {indicator_id: {"role": role, "weight": ROLE_WEIGHTS[role]} for indicator_id in indicator_ids}


DIMENSIONS = [
    {"id": "external_financial_pressure", "name": "外部金融压力", "members": {
        **member("core", "us10y", "dxy", "vix", "usdcny"), **member("secondary", "us2y", "cfets_rmb")},
     "labels": ("外部金融顺风", "外部金融中性", "外部金融逆风")},
    {"id": "global_demand", "name": "全球需求 / 外需", "members": {
        **member("core", "us_ism_man", "oecd_cli", "global_trade", "china_exports"),
        **member("secondary", "copper", "us_nonfarm", "us_unemployment", "us_ism_services"), **member("auxiliary", "brent")},
     "labels": ("外需顺风", "外需中性", "外需拖累")},
    {"id": "china_production", "name": "中国生产 / 景气", "members": {
        **member("core", "china_industrial", "china_pmi_man", "china_gdp"),
        **member("secondary", "china_pmi_composite", "china_exports", "china_hightech_output"), **member("auxiliary", "china_pmi_nonman")},
     "labels": ("生产景气改善", "生产平稳", "生产走弱")},
    {"id": "china_domestic_demand", "name": "中国内需 / 居民需求", "members": {
        **member("core", "china_retail", "china_imports", "china_unemployment"),
        **member("secondary", "china_youth_unemployment", "china_fai", "china_fai_manufacturing", "china_fai_infrastructure"),
        **member("auxiliary", "csi300", "hsi")},
     "labels": ("内需改善", "内需平稳", "内需偏弱")},
    {"id": "credit_expansion", "name": "信用扩张", "members": {
        **member("core", "china_tsf", "china_new_loans", "china_corp_long_loans", "china_household_long_loans"),
        **member("secondary", "china_m2", "china_gov_bonds", "china_bill_financing")},
     "labels": ("信用总量扩张，结构较好", "信用中性 / 结构分化", "信用偏弱")},
    {"id": "real_estate_cycle", "name": "地产周期", "members": {
        **member("core", "china_property_sales", "china_property_sales_value", "china_property_investment", "china_property_starts"),
        **member("secondary", "china_house_price", "china_household_long_loans"), **member("auxiliary", "china_property")},
     "labels": ("地产修复", "地产企稳 / 分化", "地产拖累")},
    {"id": "price_pressure", "name": "价格 / 通胀通缩压力", "members": {
        **member("core", "china_ppi", "china_cpi"), **member("secondary", "brent", "copper"), **member("auxiliary", "china_industrial")},
     "labels": ("价格温和修复", "价格平稳 / 分化", "通缩压力或成本压力")},
    {"id": "innovation_upgrade", "name": "创新升级", "members": {
        **member("core", "china_rd", "china_hightech_output", "china_hightech_investment"),
        **member("secondary", "china_hightech_exports", "china_mechanical_exports", "china_patents", "china_pct_patents", "china_triadic_patents")},
     "labels": ("创新升级增强", "创新升级平稳", "创新升级放缓")},
]


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _sign(value: float | None, threshold: float = 0.0) -> int | None:
    if value is None:
        return None
    return 1 if value > threshold else -1 if value < -threshold else 0


def _pct(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    return (current / previous - 1) * 100


def _history_values(item: dict[str, Any]) -> list[float]:
    return [value for row in (item.get("history") or []) if (value := _number(row.get("value"))) is not None]


def _three_period_direction(values: list[float]) -> int | None:
    if len(values) < 3:
        return None
    moves = [_sign(values[-2] - values[-3]), _sign(values[-1] - values[-2])]
    if moves[0] == moves[1]:
        return moves[0]
    return 0


def _seasonal_flow_direction(values: list[float]) -> tuple[int | None, str]:
    if len(values) < 13:
        return None, "insufficient_same_period_history"
    same_period = _pct(values[-1], values[-13])
    if len(values) >= 15:
        current_ma = sum(values[-3:]) / 3
        prior_ma = sum(values[-15:-12]) / 3
        rolling = _pct(current_ma, prior_ma)
        directions = [_sign(same_period, 1.0), _sign(rolling, 1.0)]
        return (directions[0] if directions[0] == directions[1] else 0), "same_period_yoy_and_3m_average"
    return _sign(same_period, 1.0), "same_period_yoy"


def _low_frequency_direction(item: dict[str, Any]) -> tuple[int | None, str]:
    indicator_id = item.get("id")
    values = _history_values(item)
    current = _number(item.get("value"))
    previous = values[-2] if len(values) >= 2 else _number(item.get("previous_value"))
    if indicator_id in SEASONAL_FLOW_IDS:
        return _seasonal_flow_direction(values)
    if indicator_id in YOY_RATE_IDS:
        change = _sign(None if current is None or previous is None else current - previous, 0.05)
        trend = _three_period_direction(values)
        return (change if trend in {None, 0, change} else 0), "yoy_rate_change_and_3_period_trend"
    if indicator_id in DIRECT_COMPARISON_IDS:
        return _sign(None if current is None or previous is None else current - previous, 0.05), "direct_previous_period"
    trend = _three_period_direction(values)
    return (trend if trend is not None else _sign(None if current is None or previous is None else current - previous, 0.05)), "level_trend"


def _daily_direction(item: dict[str, Any]) -> tuple[int | None, str]:
    threshold = DAILY_THRESHOLDS.get(item.get("id"), 0.25)
    five = _sign(_number(item.get("five_change")), threshold)
    twenty = _sign(_number(item.get("twenty_change")), threshold)
    if five is None or twenty is None:
        return None, "insufficient_5d_20d_history"
    return (five if five == twenty else 0), "5d_20d_direction"


def _oil_contributions(item: dict[str, Any]) -> dict[str, int]:
    five = _number(item.get("five_change"))
    values = _history_values(item)
    changes = [_pct(values[index], values[index - 5]) for index in range(5, len(values))]
    changes = [value for value in changes if value is not None]
    volatility = statistics.pstdev(changes[-120:]) if len(changes) >= 10 else 4.0
    moderate = max(1.0, volatility * 0.5)
    extreme = max(6.0, volatility * 1.5)
    if five is None or abs(five) < moderate:
        return {"global_demand": 0, "price_pressure": 0}
    if five >= extreme:
        return {"global_demand": 0, "price_pressure": -1}
    if five > 0:
        return {"global_demand": 1, "price_pressure": 0}
    if five <= -extreme:
        return {"global_demand": -1, "price_pressure": -1}
    return {"global_demand": -1, "price_pressure": 0}


def _price_contribution(item: dict[str, Any], direction: int) -> int:
    current = _number(item.get("value"))
    previous = _number(item.get("previous_value"))
    if item.get("id") == "china_cpi" and current is not None:
        if current < 0 or current > 3.5:
            return -1
        return 1 if 0.5 <= current <= 3.0 and direction >= 0 else 0
    if item.get("id") == "china_ppi" and current is not None and previous is not None:
        return 1 if abs(current) < abs(previous) else -1 if current < 0 and current < previous else 0
    return direction


def _dimension_contributions(item: dict[str, Any], raw_direction: int) -> dict[str, int]:
    indicator_id = item.get("id")
    if indicator_id in {"brent", "wti"}:
        return _oil_contributions(item)
    relevant = [dimension["id"] for dimension in DIMENSIONS if indicator_id in dimension["members"]]
    base = -raw_direction if indicator_id in INVERSE_IDS else raw_direction
    contributions = {dimension_id: base for dimension_id in relevant}
    if "price_pressure" in contributions:
        contributions["price_pressure"] = _price_contribution(item, raw_direction)
    # Equity prices remain auxiliary expectations only; the weight and core gate
    # prevent them from determining domestic-demand conclusions by themselves.
    return contributions


def score_indicators(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in indicators:
        frequency = item.get("frequency", "daily")
        age = item.get("age_days")
        limit = int(item.get("analysis_validity_days", ANALYSIS_VALIDITY_DAYS.get(frequency, 45)))
        if item.get("status") == "failed" or item.get("value") is None:
            data_status = "missing"
        elif item.get("status") != "ok" or age is None or age > limit:
            data_status = "stale"
        elif item.get("released_at") == datetime.now().date().isoformat() or item.get("value_changed_since_last_run") is True:
            data_status = "new_update"
        else:
            data_status = "current_valid"
        history_count = len(_history_values(item))
        history_required = HISTORY_REQUIREMENTS.get(frequency, 0)
        history_status = "sufficient" if history_count >= history_required else "history_insufficient"
        direction, method = (_daily_direction(item) if frequency == "daily" else _low_frequency_direction(item))
        usable_for_score = data_status in {"new_update", "current_valid"} and history_status == "sufficient" and direction is not None
        contributions = {} if not usable_for_score else _dimension_contributions(item, direction)
        base_score = None if not usable_for_score else (-direction if item.get("id") in INVERSE_IDS else direction)
        results.append({
            "indicator_id": item.get("id"), "indicator_name": item.get("name", item.get("id")),
            "value": item.get("value"), "frequency": frequency, "date": item.get("date"),
            "observation_period": item.get("observation_period"), "released_at": item.get("released_at"),
            "fetched_at": item.get("fetched_at"), "value_changed_since_last_run": item.get("value_changed_since_last_run"),
            "source": item.get("source"), "base_change": None if direction is None else ("up" if direction > 0 else "down" if direction < 0 else "flat"),
            "comparison_method": method, "indicator_score": base_score, "dimension_contributions": contributions,
            "status": "current" if data_status in {"new_update", "current_valid"} else "stale",
            "data_status": data_status, "history_status": history_status, "history_points": history_count,
            "history_required": history_required, "age_days": age, "freshness_limit_days": limit,
        })
    return results


def _confidence(coverage: float, core_coverage: float, agreement: float, history_coverage: float, usable_core: int) -> str:
    if usable_core < 1 or core_coverage < 0.34:
        return "低"
    if coverage >= 0.65 and core_coverage >= 0.6 and agreement >= 0.7 and history_coverage >= 0.8 and usable_core >= 2:
        return "高"
    if coverage >= 0.4 and core_coverage >= 0.5 and history_coverage >= 0.6:
        return "中"
    return "低"


def _driver_text(item: dict[str, Any], contribution: int) -> str:
    return f"{item['indicator_name']}{'改善' if contribution > 0 else '走弱'}"


def _credit_label(score: float | None, confidence: str, usable: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    corp = usable.get("china_corp_long_loans", {}).get("contribution")
    household = usable.get("china_household_long_loans", {}).get("contribution")
    gov = usable.get("china_gov_bonds", {}).get("contribution")
    bills = usable.get("china_bill_financing", {}).get("contribution")
    structure_known = corp is not None and household is not None and gov is not None and bills is not None
    effective = bool(score is not None and score >= 0.5 and confidence in {"中", "高"} and structure_known and corp == 1 and household >= 0 and bills != 1)
    if score is not None and score >= 0.5:
        label = "信用有效扩张" if effective else "信用总量信号偏强，结构待验证"
    elif score is not None and score <= -0.5:
        label = "信用偏弱"
    else:
        label = "信用中性 / 结构分化"
    return label, {"total_judgement": "扩张" if score is not None and score >= 0.5 else "偏弱" if score is not None and score <= -0.5 else "中性", "structure_judgement": "结构较好" if effective else "结构待验证" if not structure_known else "结构分化", "effective_expansion": effective}


def _estate_label(score: float | None, confidence: str, usable_core: int, usable: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    sales_values = [usable.get(item_id, {}).get("contribution") for item_id in ("china_property_sales", "china_property_sales_value")]
    development_values = [usable.get(item_id, {}).get("contribution") for item_id in ("china_property_investment", "china_property_starts")]
    sales = next((value for value in sales_values if value is not None), None)
    development = next((value for value in development_values if value is not None), None)
    price = usable.get("china_house_price", {}).get("contribution")
    if usable_core < 2:
        if score is not None and score <= -0.3:
            label = "地产信号偏弱，但证据不足"
        elif score is not None and score >= 0.3:
            label = "地产信号偏稳，但证据不足"
        else:
            label = "地产信号偏稳，但证据不足"
    elif sales == 1 and development == -1:
        label = "地产销售端边际改善，开发端仍弱"
    elif score is not None and score <= -0.5:
        label = "地产拖累" if confidence in {"中", "高"} and usable_core >= 2 else "地产信号偏弱，但证据不足"
    elif score is not None and score >= 0.5:
        label = "地产修复"
    else:
        label = "地产企稳 / 分化"
    return label, {"sales_side": "改善" if sales == 1 else "走弱" if sales == -1 else "数据不足", "development_side": "改善" if development == 1 else "走弱" if development == -1 else "数据不足", "price_side": "改善" if price == 1 else "走弱" if price == -1 else "数据不足"}


def build_dimension_scores(indicators: list[dict[str, Any]], indicator_scores: list[dict[str, Any]], as_of: datetime | None = None) -> list[dict[str, Any]]:
    score_map = {item["indicator_id"]: item for item in indicator_scores}
    output: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        members = dimension["members"]
        present = [score_map[item_id] for item_id in members if item_id in score_map]
        available_rows: list[dict[str, Any]] = []
        usable_rows: list[dict[str, Any]] = []
        for item_id, config in members.items():
            item = score_map.get(item_id)
            contribution = (item or {}).get("dimension_contributions", {}).get(dimension["id"])
            if item and item.get("data_status") in {"new_update", "current_valid"}:
                available_rows.append({**item, **config, "contribution": contribution})
            if item and item.get("data_status") in {"new_update", "current_valid"} and contribution is not None:
                usable_rows.append({**item, **config, "contribution": contribution})
        usable = {item["indicator_id"]: item for item in usable_rows}
        weighted_total = sum(item["contribution"] * item["weight"] for item in usable_rows)
        weight_total = sum(item["weight"] for item in usable_rows)
        score = round(weighted_total / weight_total, 2) if weight_total else None
        direction = 1 if score is not None and score >= 0.5 else -1 if score is not None and score <= -0.5 else 0
        agreement_weight = sum(item["weight"] for item in usable_rows if item["contribution"] == direction)
        agreement = agreement_weight / weight_total if weight_total else 0
        coverage = len(available_rows) / len(members)
        freshness = len(available_rows) / len(present) if present else 0
        usable_core = sum(1 for item in usable_rows if item["role"] == "core")
        available_core = sum(1 for item in available_rows if item["role"] == "core")
        expected_core = sum(1 for item in members.values() if item["role"] == "core")
        core_coverage = available_core / expected_core if expected_core else 0
        history_sufficient = sum(1 for item in available_rows if item.get("history_status") == "sufficient")
        history_coverage = history_sufficient / len(available_rows) if available_rows else 0
        confidence = _confidence(coverage, core_coverage, agreement, history_coverage, usable_core)
        label = "数据不足" if score is None else dimension["labels"][0 if direction > 0 else 2 if direction < 0 else 1]
        diagnostics: dict[str, Any] = {}
        if dimension["id"] == "credit_expansion":
            label, diagnostics = _credit_label(score, confidence, usable)
        elif dimension["id"] == "real_estate_cycle":
            label, diagnostics = _estate_label(score, confidence, usable_core, usable)
        evidence_quality = "strong" if confidence == "高" and usable_core >= max(2, math.ceil(expected_core * 0.6)) else "medium" if confidence == "中" else "weak"
        can_enter = bool(evidence_quality != "weak" and score is not None and abs(score) >= 0.5 and usable_core >= 2)
        can_state = bool(evidence_quality != "weak" and usable_core >= 2)
        today = (as_of or datetime.now()).date().isoformat()
        updated = [item["indicator_name"] for item in usable_rows if item.get("released_at") == today or item.get("value_changed_since_last_run") is True]
        if dimension["id"] == "innovation_upgrade" and not updated:
            can_enter = False
        positive = [_driver_text(item, item["contribution"]) for item in usable_rows if item["contribution"] > 0][:3]
        negative = [_driver_text(item, item["contribution"]) for item in usable_rows if item["contribution"] < 0][:3]
        stale = [item["indicator_name"] for item in present if item.get("data_status") == "stale"]
        missing = [item_id for item_id in members if item_id not in score_map or score_map[item_id].get("data_status") == "missing"]
        history_insufficient = [item["indicator_name"] for item in available_rows if item.get("history_status") == "history_insufficient"]
        output.append({
            "dimension_id": dimension["id"], "dimension_name": dimension["name"], "score": score, "label": label,
            "confidence": confidence, "evidence_quality": evidence_quality, "can_enter_summary": can_enter, "can_be_macro_state": can_state,
            "coverage": round(coverage, 2), "freshness": round(freshness, 2), "agreement": round(agreement, 2),
            "core_coverage": round(core_coverage, 2), "history_coverage": round(history_coverage, 2),
            "usable_core_indicators": usable_core, "available_core_indicators": available_core, "expected_core_indicators": expected_core,
            "top_positive_drivers": positive, "top_negative_drivers": negative, "updated_indicators": updated,
            "stale_indicators": stale, "missing_indicators": missing, "history_insufficient_indicators": history_insufficient,
            "short_explanation": f"按核心/次要/辅助权重计算；{available_core}/{expected_core}项核心指标在有效期内，{usable_core}项可计算方向。",
            **diagnostics,
        })
    return output


def build_data_freshness(indicator_scores: list[dict[str, Any]], generated_at: datetime) -> dict[str, list[str]]:
    new_updates = [item["indicator_name"] for item in indicator_scores if item.get("data_status") == "new_update"]
    recent = [item["indicator_name"] for item in indicator_scores if item.get("data_status") == "current_valid"]
    stale = [item["indicator_name"] for item in indicator_scores if item.get("data_status") == "stale"]
    missing = [item["indicator_name"] for item in indicator_scores if item.get("data_status") == "missing"]
    history_insufficient = [item["indicator_name"] for item in indicator_scores if item.get("history_status") == "history_insufficient" and item.get("data_status") in {"new_update", "current_valid"}]
    return {"new_updates_today": new_updates, "recent_indicators": recent, "stale_indicators": stale, "missing_indicators": missing, "history_insufficient": history_insufficient}
