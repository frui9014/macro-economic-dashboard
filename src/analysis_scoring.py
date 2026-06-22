from __future__ import annotations

from datetime import datetime
from typing import Any


ANALYSIS_FRESHNESS_DAYS = {"daily": 3, "weekly": 14, "monthly": 45, "quarterly": 120, "annual": 450}

INVERSE_IDS = {
    "us10y", "us2y", "dxy", "vix", "usdcny", "us_unemployment",
    "china_unemployment", "china_youth_unemployment",
}

DAILY_THRESHOLDS = {
    "us10y": 5.0, "us2y": 5.0, "dxy": 0.3, "vix": 5.0,
    "usdcny": 0.3, "csi300": 0.5, "hsi": 0.5, "hscei": 0.5,
    "china10y": 5.0, "brent": 0.8, "wti": 0.8, "copper": 0.6,
}

DIMENSIONS = [
    {
        "id": "external_financial_pressure", "name": "外部金融压力",
        "ids": ["us10y", "us2y", "dxy", "vix", "usdcny", "cfets_rmb"],
        "labels": ("外部金融顺风", "外部金融中性", "外部金融逆风"),
    },
    {
        "id": "global_demand", "name": "全球需求 / 外需",
        "ids": ["us_ism_man", "us_ism_services", "us_nonfarm", "us_unemployment", "oecd_cli", "global_trade", "copper", "brent", "china_exports"],
        "labels": ("外需顺风", "外需中性", "外需拖累"),
    },
    {
        "id": "china_production", "name": "中国生产 / 景气",
        "ids": ["china_gdp", "china_pmi_man", "china_pmi_nonman", "china_pmi_composite", "china_industrial", "china_exports", "china_hightech_output"],
        "labels": ("生产景气改善", "生产平稳", "生产走弱"),
    },
    {
        "id": "china_domestic_demand", "name": "中国内需 / 居民需求",
        "ids": ["china_retail", "china_fai", "china_fai_manufacturing", "china_fai_infrastructure", "china_imports", "china_unemployment", "china_youth_unemployment", "csi300", "hsi"],
        "labels": ("内需改善", "内需平稳", "内需偏弱"),
    },
    {
        "id": "credit_expansion", "name": "信用扩张",
        "ids": ["china_tsf", "china_m2", "china_new_loans", "china_corp_long_loans", "china_household_long_loans", "china_gov_bonds", "china_bill_financing"],
        "labels": ("信用有效扩张", "信用中性 / 结构分化", "信用偏弱"),
    },
    {
        "id": "real_estate_cycle", "name": "地产周期",
        "ids": ["china_property_sales", "china_property_sales_value", "china_property_investment", "china_property_starts", "china_house_price", "china_household_long_loans", "china_property"],
        "labels": ("地产修复", "地产企稳 / 分化", "地产继续拖累"),
    },
    {
        "id": "price_pressure", "name": "价格 / 通胀通缩压力",
        "ids": ["china_cpi", "china_ppi", "brent", "copper", "china_industrial"],
        "labels": ("价格温和修复", "价格平稳 / 分化", "通缩压力或成本压力"),
    },
    {
        "id": "innovation_upgrade", "name": "创新升级",
        "ids": ["china_rd", "china_hightech_output", "china_hightech_investment", "china_patents", "china_pct_patents", "china_triadic_patents", "china_hightech_exports", "china_mechanical_exports"],
        "labels": ("创新升级增强", "创新升级平稳", "创新升级放缓"),
    },
]


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if result == result else None
    except (TypeError, ValueError):
        return None


def _movement(current: float | None, previous: float | None, tolerance: float = 0.05) -> int:
    if current is None or previous is None:
        return 0
    scale = max(abs(previous), 1.0)
    change = (current - previous) / scale * 100
    return 1 if change > tolerance else -1 if change < -tolerance else 0


def _recent_trend(item: dict[str, Any]) -> int:
    history = item.get("history") or []
    values = [_number(row.get("value")) for row in history[-3:]]
    values = [value for value in values if value is not None]
    if len(values) < 2:
        return 0
    return _movement(values[-1], values[0])


def _daily_score(item: dict[str, Any]) -> int:
    threshold = DAILY_THRESHOLDS.get(item.get("id"), 0.25)
    moves = [_number(item.get("five_change")), _number(item.get("twenty_change"))]
    signs = [1 if value is not None and value >= threshold else -1 if value is not None and value <= -threshold else 0 for value in moves]
    score = signs[0] if signs[0] == signs[1] else 0
    if item.get("id") in INVERSE_IDS:
        score *= -1
    if item.get("id") in {"brent", "wti"}:
        # Oil is not a monotonic China-macro signal: sharp moves in either direction need context.
        return 0 if score > 0 else score
    return score


def _low_frequency_score(item: dict[str, Any]) -> int:
    indicator_id = item.get("id")
    current = _number(item.get("value"))
    previous = _number(item.get("previous_value"))
    change_score = _movement(current, previous)
    trend_score = _recent_trend(item)

    if indicator_id in {"china_pmi_man", "china_pmi_nonman", "china_pmi_composite", "us_ism_man", "us_ism_services"} and current is not None:
        level = 1 if current >= 50 else -1
        score = level if change_score in {0, level} else 0
    elif indicator_id == "china_cpi" and current is not None:
        if current < 0 or current > 3.5:
            score = -1
        elif 0.5 <= current <= 3.0 and change_score >= 0:
            score = 1
        else:
            score = 0
    elif indicator_id == "china_ppi" and current is not None and previous is not None:
        score = 1 if abs(current) < abs(previous) else -1 if current < previous and current < 0 else change_score
    else:
        score = change_score if change_score == trend_score else change_score if trend_score == 0 else 0

    if indicator_id in INVERSE_IDS:
        score *= -1
    return max(-1, min(1, score))


def score_indicators(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in indicators:
        status = item.get("status")
        age = item.get("age_days")
        limit = ANALYSIS_FRESHNESS_DAYS.get(item.get("frequency", "daily"), 45)
        stale = status != "ok" or age is None or age > limit
        score = None if stale else (_daily_score(item) if item.get("frequency", "daily") == "daily" else _low_frequency_score(item))
        results.append({
            "indicator_id": item.get("id"),
            "indicator_name": item.get("name", item.get("id")),
            "frequency": item.get("frequency", "daily"),
            "date": item.get("date"),
            "value": item.get("value"),
            "indicator_score": score,
            "status": "stale" if stale else "current",
            "age_days": age,
            "freshness_limit_days": limit,
        })
    return results


def _confidence(coverage: float, freshness: float, agreement: float, available: int) -> str:
    if available < 2:
        return "低"
    if coverage >= 0.6 and freshness >= 0.7 and agreement >= 0.7:
        return "高"
    if coverage >= 0.4 and freshness >= 0.5:
        return "中"
    return "低"


def _driver_text(item: dict[str, Any]) -> str:
    suffix = "改善" if item["indicator_score"] == 1 else "走弱"
    return f"{item['indicator_name']}{suffix}"


def build_dimension_scores(indicators: list[dict[str, Any]], indicator_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    score_map = {item["indicator_id"]: item for item in indicator_scores}
    raw_map = {item.get("id"): item for item in indicators}
    output: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        expected = dimension["ids"]
        present = [score_map[item_id] for item_id in expected if item_id in score_map]
        usable = [item for item in present if item["indicator_score"] is not None]
        stale = [item for item in present if item["status"] == "stale"]
        missing_ids = [item_id for item_id in expected if item_id not in score_map]
        values = [item["indicator_score"] for item in usable]
        score = round(sum(values) / len(values), 2) if values else None
        direction = 1 if score is not None and score >= 0.5 else -1 if score is not None and score <= -0.5 else 0
        agreement = (sum(1 for value in values if value == direction) / len(values)) if values and direction else (sum(1 for value in values if value == 0) / len(values) if values else 0)
        coverage = len(present) / len(expected)
        freshness = len(usable) / len(present) if present else 0
        confidence = _confidence(coverage, freshness, agreement, len(usable))
        label = "数据不足" if score is None else dimension["labels"][0 if direction > 0 else 2 if direction < 0 else 1]
        positive = [_driver_text(item) for item in usable if item["indicator_score"] > 0][:3]
        negative = [_driver_text(item) for item in usable if item["indicator_score"] < 0][:3]
        updated = [item["indicator_name"] for item in usable if (item.get("age_days") or 0) <= 1]
        missing_names = [raw_map.get(item_id, {}).get("name", item_id) for item_id in missing_ids]
        explanation = f"基于{len(usable)}/{len(expected)}项有效指标，正向{len(positive)}项、负向{len(negative)}项。"
        if dimension["id"] == "innovation_upgrade":
            explanation += "创新升级属于慢变量，仅在相关数据更新时重点解读。"
        output.append({
            "dimension_id": dimension["id"], "dimension_name": dimension["name"],
            "score": score, "label": label, "confidence": confidence,
            "coverage": round(coverage, 2), "freshness": round(freshness, 2), "agreement": round(agreement, 2),
            "top_positive_drivers": positive, "top_negative_drivers": negative,
            "updated_indicators": updated,
            "stale_indicators": [item["indicator_name"] for item in stale],
            "missing_indicators": missing_names,
            "short_explanation": explanation,
        })
    return output


def build_data_freshness(indicator_scores: list[dict[str, Any]], generated_at: datetime) -> dict[str, list[str]]:
    new_updates: list[str] = []
    recent: list[str] = []
    stale: list[str] = []
    for item in indicator_scores:
        if item["status"] == "stale":
            stale.append(item["indicator_name"])
        elif (item.get("age_days") or 0) <= 1:
            new_updates.append(item["indicator_name"])
        else:
            recent.append(item["indicator_name"])
    return {
        "new_updates_today": new_updates,
        "recent_indicators": recent,
        "stale_indicators": stale,
        "missing_indicators": [],
    }
