from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from macro_catalog import CATALOG, fetch_catalog_item, period_key, should_scan
from analysis_scoring import build_data_freshness, build_dimension_scores, score_indicators
from divergence_detector import detect_divergences
from gpt_macro_report import generate_gpt_judgement, render_markdown, rule_summary
from macro_state_detector import detect_macro_states
from relation_diagnostics import build_relation_diagnostics


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "web"
SITE_ROOT = PROJECT_ROOT / "site"
DATA_ROOT = PROJECT_ROOT / "data" / "processed"
ANALYSIS_ROOT = PROJECT_ROOT / "data" / "analysis"
PROMPTS_ROOT = PROJECT_ROOT / "prompts"
DEFAULT_PUBLIC_ROOT = PROJECT_ROOT.parents[1] / "outputs" / "macro-economic-dashboard"
BEIJING = ZoneInfo("Asia/Shanghai")

YAHOO_SERIES = [
    {
        "id": "dxy",
        "name": "美元指数",
        "symbol": "DX-Y.NYB",
        "unit": "点",
        "decimals": 2,
        "group": "全球市场",
        "meaning": "美元走强通常收紧非美经济体的金融条件。",
        "consequence_up": "若持续走强，人民币与新兴市场资产通常面临更大外部压力。",
        "consequence_down": "若持续回落，非美资产和跨境流动性压力可能缓解。",
        "source": "Yahoo Finance / ICE DXY",
    },
    {
        "id": "vix",
        "name": "VIX",
        "symbol": "^VIX",
        "unit": "点",
        "decimals": 2,
        "group": "全球市场",
        "meaning": "VIX 反映美股期权隐含波动和全球避险温度。",
        "consequence_up": "若持续上升，风险资产估值与跨境风险偏好可能承压。",
        "consequence_down": "若持续下降，通常意味着市场风险偏好趋于稳定。",
        "source": "Yahoo Finance / CBOE",
    },
    {
        "id": "brent",
        "name": "Brent 原油",
        "symbol": "BZ=F",
        "unit": "美元/桶",
        "decimals": 2,
        "group": "全球市场",
        "meaning": "油价同时受全球需求、供给约束和地缘事件影响。",
        "consequence_up": "若持续上升，能源通胀和企业成本压力可能增加。",
        "consequence_down": "若持续下降，通胀压力可能缓解，但也需排查需求走弱。",
        "source": "Yahoo Finance / ICE Brent",
    },
    {
        "id": "copper",
        "name": "铜",
        "symbol": "HG=F",
        "unit": "美分/磅",
        "decimals": 2,
        "group": "全球市场",
        "meaning": "铜价常被用于观察全球制造业与基建需求预期。",
        "consequence_up": "若需求因素主导，持续上行可能预示制造业预期改善。",
        "consequence_down": "若持续回落，可能提示全球工业需求预期转弱。",
        "source": "Yahoo Finance / COMEX",
    },
    {
        "id": "usdcny",
        "name": "USD/CNY",
        "symbol": "CNY=X",
        "unit": "人民币/美元",
        "decimals": 4,
        "group": "中国市场",
        "meaning": "数值上升表示人民币对美元走弱，需结合美元指数共同判断。",
        "consequence_up": "若与美元同步走强，外部金融约束可能加大。",
        "consequence_down": "若持续回落，人民币外部压力可能缓解。",
        "source": "Yahoo Finance / 公开外汇行情",
    },
    {
        "id": "csi300",
        "name": "沪深 300",
        "symbol": "000300.SS",
        "unit": "点",
        "decimals": 2,
        "group": "中国市场",
        "meaning": "反映大型 A 股公司的市场表现和国内政策、增长预期。",
        "consequence_up": "若与信用和基本面共振，可能意味着增长预期改善。",
        "consequence_down": "若持续回落，可能反映风险偏好或增长预期承压。",
        "source": "Yahoo Finance / 中证指数",
    },
    {
        "id": "hsi",
        "name": "恒生指数",
        "symbol": "^HSI",
        "unit": "点",
        "decimals": 2,
        "group": "中国市场",
        "meaning": "同时受中国增长预期和全球美元流动性影响。",
        "consequence_up": "若与 A 股同步走强，市场对中国资产的预期可能改善。",
        "consequence_down": "若弱于 A 股，全球流动性或离岸风险偏好可能构成额外压力。",
        "source": "Yahoo Finance / 恒生指数公司",
    },
]


def http_get(url: str, timeout: int = 45) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 MacroEconomicObservatory/0.1",
            "Accept": "application/json,text/xml,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def pct_change(current: float, previous: float) -> float | None:
    if not finite(current) or not finite(previous) or previous == 0:
        return None
    return (current / previous - 1) * 100


def fetch_yahoo(config: dict[str, Any]) -> dict[str, Any]:
    symbol = urllib.parse.quote(config["symbol"], safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d&events=history"
    payload = json.loads(http_get(url).decode("utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    closes = quote.get("close") or []
    points = []
    for timestamp, close in zip(timestamps, closes):
        if finite(close):
            date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
            points.append({"date": date, "value": round(float(close), 6)})
    if len(points) < 2:
        raise ValueError(f"{config['name']} 有效观测不足")
    return build_indicator(config, points, url)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if local_name(child.tag).upper() == name.upper():
            return child.text
    return None


def fetch_treasury() -> list[dict[str, Any]]:
    year = datetime.now(BEIJING).year
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        f"?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
    )
    root = ET.fromstring(http_get(url))
    rows: list[dict[str, Any]] = []
    for element in root.iter():
        date_text = child_text(element, "NEW_DATE")
        two_text = child_text(element, "BC_2YEAR")
        ten_text = child_text(element, "BC_10YEAR")
        if date_text and (two_text or ten_text):
            try:
                date = datetime.fromisoformat(date_text.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                continue
            rows.append(
                {
                    "date": date,
                    "us2y": float(two_text) if two_text else None,
                    "us10y": float(ten_text) if ten_text else None,
                }
            )
    unique = {row["date"]: row for row in rows}
    ordered = [unique[key] for key in sorted(unique)]
    output = []
    for indicator_id, name, field in (
        ("us2y", "美国 2 年期国债", "us2y"),
        ("us10y", "美国 10 年期国债", "us10y"),
    ):
        points = [
            {"date": row["date"], "value": row[field]}
            for row in ordered
            if finite(row[field])
        ]
        config = {
            "id": indicator_id,
            "name": name,
            "unit": "%",
            "decimals": 2,
            "group": "全球利率",
            "meaning": "美国国债收益率是全球资产定价和美元金融条件的重要锚。",
            "consequence_up": "若持续上行，融资成本和风险资产估值压力可能增加。",
            "consequence_down": "若持续回落，全球金融条件可能边际缓和，但也可能反映增长担忧。",
            "source": "U.S. Department of the Treasury",
        }
        output.append(build_indicator(config, points, url, basis_points=True))
    return output


def build_indicator(
    config: dict[str, Any],
    points: list[dict[str, Any]],
    source_url: str,
    basis_points: bool = False,
) -> dict[str, Any]:
    latest = points[-1]
    previous = points[-2]
    five_back = points[max(0, len(points) - 6)]
    twenty_back = points[max(0, len(points) - 21)]
    if basis_points:
        day_change = (latest["value"] - previous["value"]) * 100
        five_change = (latest["value"] - five_back["value"]) * 100
        twenty_change = (latest["value"] - twenty_back["value"]) * 100
        change_unit = "bp"
    else:
        day_change = pct_change(latest["value"], previous["value"])
        five_change = pct_change(latest["value"], five_back["value"])
        twenty_change = pct_change(latest["value"], twenty_back["value"])
        change_unit = "%"
    direction = "up" if (day_change or 0) > 0.01 else "down" if (day_change or 0) < -0.01 else "flat"
    reason = config["meaning"]
    consequence = config["consequence_up"] if direction == "up" else config["consequence_down"] if direction == "down" else "当前变化较小，暂不足以单独改变宏观判断。"
    return {
        "id": config["id"],
        "name": config["name"],
        "group": config["group"],
        "value": latest["value"],
        "unit": config["unit"],
        "decimals": config["decimals"],
        "date": latest["date"],
        "day_change": round(day_change, 4) if finite(day_change) else None,
        "five_change": round(five_change, 4) if finite(five_change) else None,
        "twenty_change": round(twenty_change, 4) if finite(twenty_change) else None,
        "change_unit": change_unit,
        "direction": direction,
        "reason": reason,
        "consequence": consequence,
        "source": config["source"],
        "source_url": source_url,
        "frequency": "daily",
        "frequency_en": "Daily",
        "history": points[-260:],
        "status": "ok",
    }


def get_indicator(indicators: list[dict[str, Any]], indicator_id: str) -> dict[str, Any] | None:
    return next((item for item in indicators if item.get("id") == indicator_id and item.get("status") == "ok" and item.get("freshness_status", "current") == "current"), None)


FRESHNESS_LIMITS = {"daily": 7, "weekly": 21, "monthly": 75, "quarterly": 160, "annual": 900}


def annotate_freshness(indicators: list[dict[str, Any]], now: datetime) -> None:
    for item in indicators:
        frequency = item.get("frequency", "daily")
        limit = int(item.get("freshness_limit_days", FRESHNESS_LIMITS.get(frequency, 75)))
        year, month, day = period_key(item.get("date"))
        if frequency == "monthly":
            day = 28
        elif frequency == "quarterly":
            month, day = min(12, max(1, month) * 3), 28
        elif frequency == "annual":
            month, day = 12, 31
        try:
            observed = datetime(year, max(1, month), max(1, day), tzinfo=BEIJING).date()
            age = max(0, (now.date() - observed).days)
            freshness = "current" if age <= limit else "stale"
        except ValueError:
            age = None
            freshness = "unknown"
        item["freshness_status"] = freshness
        item["age_days"] = age
        item["freshness_limit_days"] = limit
        item["eligible_for_signal"] = item.get("status") == "ok" and freshness == "current"


def move_score(item: dict[str, Any] | None, threshold: float, inverse: bool = False) -> int:
    if not item or not finite(item.get("day_change")):
        return 0
    value = item["day_change"]
    score = 1 if value >= threshold else -1 if value <= -threshold else 0
    return -score if inverse else score


def build_dimensions(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    us10y = get_indicator(indicators, "us10y")
    dxy = get_indicator(indicators, "dxy")
    vix = get_indicator(indicators, "vix")
    liquidity_score = (
        move_score(us10y, 5)
        + move_score(dxy, 0.3)
        + move_score(vix, 5)
    )
    liquidity = "收紧" if liquidity_score >= 2 else "宽松" if liquidity_score <= -2 else "中性"

    copper = get_indicator(indicators, "copper")
    brent = get_indicator(indicators, "brent")
    demand_score = move_score(copper, 0.6) + move_score(brent, 0.8)
    demand = "上行" if demand_score >= 2 else "下行" if demand_score <= -2 else "平稳"

    csi = get_indicator(indicators, "csi300")
    hsi = get_indicator(indicators, "hsi")
    china_market_score = move_score(csi, 0.5) + move_score(hsi, 0.5)
    china_market = "预期改善" if china_market_score >= 2 else "预期承压" if china_market_score <= -2 else "预期平稳"

    oil_score = move_score(brent, 0.8)
    inflation = "市场压力上升" if oil_score > 0 else "市场压力下降" if oil_score < 0 else "稳定"

    return [
        {"name": "全球流动性", "status": liquidity, "confidence": "中", "freshness": "日频市场信号"},
        {"name": "全球需求", "status": demand, "confidence": "低", "freshness": "大宗商品代理"},
        {"name": "中国增长", "status": china_market, "confidence": "低", "freshness": "仅市场预期"},
        {"name": "中国内需", "status": "待宏观数据", "confidence": "—", "freshness": "月度"},
        {"name": "中国地产", "status": "待宏观数据", "confidence": "—", "freshness": "月度"},
        {"name": "中国信用", "status": "待宏观数据", "confidence": "—", "freshness": "月度"},
        {"name": "通胀压力", "status": inflation, "confidence": "低", "freshness": "能源市场代理"},
        {"name": "创新升级", "status": "待结构数据", "confidence": "—", "freshness": "月度/年度"},
    ]


def build_combinations(indicators: list[dict[str, Any]], dimensions: list[dict[str, Any]]) -> list[dict[str, str]]:
    dimension_map = {item["name"]: item["status"] for item in dimensions}
    dxy = get_indicator(indicators, "dxy")
    cny = get_indicator(indicators, "usdcny")
    csi = get_indicator(indicators, "csi300")
    hsi = get_indicator(indicators, "hsi")
    copper = get_indicator(indicators, "copper")
    items = [
        {
            "title": "全球金融条件",
            "signal": dimension_map.get("全球流动性", "中性"),
            "analysis": "由美国 10 年期收益率、美元和 VIX 的同向或分化变化共同判断；它描述市场金融条件，不替代美联储政策判断。",
        }
    ]
    if dxy and cny:
        same = (dxy["day_change"] or 0) * (cny["day_change"] or 0) > 0
        items.append(
            {
                "title": "美元—人民币联动",
                "signal": "外部压力同向" if same and (dxy["day_change"] or 0) > 0 else "联动分化" if not same else "外部压力缓和",
                "analysis": "美元与 USD/CNY 同向上升时，人民币走弱更可能包含全球美元因素；若二者分化，应更多检查中国自身预期与跨境资金因素。",
            }
        )
    if csi and hsi:
        same = (csi["day_change"] or 0) * (hsi["day_change"] or 0) > 0
        items.append(
            {
                "title": "中国资产共振",
                "signal": "同向" if same else "分化",
                "analysis": "A 股与港股同向时，增长或政策预期信号更一致；分化时通常需要区分国内因素与全球流动性影响。",
            }
        )
    if copper:
        items.append(
            {
                "title": "全球需求温度",
                "signal": dimension_map.get("全球需求", "平稳"),
                "analysis": "铜和原油只提供高频需求线索，价格也会受到供给与地缘事件影响，必须等待贸易和景气数据确认。",
            }
        )
    return items[:3]


def build_learning_note(dimensions: list[dict[str, Any]]) -> str:
    mapping = {item["name"]: item["status"] for item in dimensions}
    liquidity = mapping.get("全球流动性", "中性")
    if liquidity == "收紧":
        return "今天最值得观察的是全球金融条件偏紧。利率、美元和波动率若持续共振上行，会同时抬升融资成本、压低资产估值并增加新兴市场汇率压力。单日变化仍不足以证明趋势，接下来要看这种共振能否延续到一周以上。"
    if liquidity == "宽松":
        return "今天的市场组合更接近全球金融条件边际宽松。利率、美元和波动率同步回落通常有利于风险资产和非美货币，但仍需确认这究竟来自通胀缓解，还是增长担忧推动的避险降息预期。"
    return "今天的全球金融条件信号总体分化。分化本身很重要：它说明市场尚未形成单一宏观叙事，此时不宜用某一个价格变化概括经济方向，应继续观察利率、美元与波动率能否形成持续共振。"


def load_previous() -> dict[str, Any] | None:
    path = DATA_ROOT / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_analysis_payload(indicators: list[dict[str, Any]], pending: list[dict[str, str]], now: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    indicator_scores = score_indicators(indicators)
    dimensions = build_dimension_scores(indicators, indicator_scores)
    relations = build_relation_diagnostics(dimensions, indicator_scores)
    divergences = detect_divergences(dimensions, indicator_scores)
    states = detect_macro_states(dimensions, indicator_scores, divergences)
    freshness = build_data_freshness(indicator_scores, now)
    dimension_missing = [name for item in dimensions for name in item.get("missing_indicators", [])]
    pending_missing = [item.get("name", "未知指标") for item in pending]
    freshness["missing_indicators"] = list(dict.fromkeys(pending_missing + dimension_missing))
    important_updates = [item for item in indicator_scores if item["indicator_name"] in freshness["new_updates_today"]]
    key_values = sorted(
        [item for item in indicator_scores if item.get("indicator_score") is not None],
        key=lambda item: (abs(item["indicator_score"]), -(item.get("age_days") or 0)),
        reverse=True,
    )[:12]
    payload = {
        "date": now.date().isoformat(),
        "generated_at": now.isoformat(timespec="seconds"),
        "purpose": "基于公开宏观数据生成每日宏观观察报告，不做投资建议",
        "data_freshness": freshness,
        "indicator_scores": indicator_scores,
        "dimension_scores": dimensions,
        "relation_diagnostics": relations,
        "detected_divergences": divergences,
        "candidate_macro_states": states,
        "important_data_updates": [{"indicator": item["indicator_name"], "date": item["date"], "score": item["indicator_score"]} for item in important_updates],
        "missing_or_stale_data": freshness["stale_indicators"] + freshness["missing_indicators"],
        "raw_key_values_summary": [{"indicator": item["indicator_name"], "date": item["date"], "value": item["value"], "score": item["indicator_score"]} for item in key_values],
    }
    payload["rule_summary"] = rule_summary(payload)
    judgement = generate_gpt_judgement(payload, PROMPTS_ROOT)
    return payload, judgement


def assemble(force_all: bool = False, force_ids: set[str] | None = None) -> dict[str, Any]:
    now = datetime.now(BEIJING)
    force_ids = force_ids or set()
    indicators: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    try:
        indicators.extend(fetch_treasury())
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "美国财政部收益率", "error": str(exc)})
    for config in YAHOO_SERIES:
        try:
            indicators.append(fetch_yahoo(config))
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": config["name"], "error": str(exc)})

    previous = load_previous()
    if previous:
        existing_ids = {item["id"] for item in indicators}
        catalog_ids = {item["id"] for item in CATALOG}
        for old in previous.get("indicators", []):
            if old.get("id") not in existing_ids and old.get("id") not in catalog_ids and old.get("status") == "ok":
                stale = dict(old)
                stale["status"] = "stale"
                stale["stale_reason"] = "本次抓取失败，保留上次有效值"
                indicators.append(stale)

    previous_catalog = {
        item.get("id"): item
        for item in (previous or {}).get("indicators", [])
        if item.get("id") in {entry["id"] for entry in CATALOG}
    }
    previous_scans = {item.get("id"): item for item in (previous or {}).get("scan_log", [])}
    previous_pending = {item.get("name"): item for item in (previous or {}).get("pending", [])}
    pending: list[dict[str, str]] = []
    scan_log: list[dict[str, str]] = []
    for catalog_item in CATALOG:
        old = previous_catalog.get(catalog_item["id"])
        last_scan = previous_scans.get(catalog_item["id"])
        schedule_state = last_scan if last_scan and last_scan.get("status") == "failed" else old or last_scan
        due, reason = should_scan(catalog_item, now, schedule_state, force=force_all or catalog_item["id"] in force_ids)
        if not due:
            if old:
                indicators.append(old)
            elif catalog_item["name"] in previous_pending:
                pending.append(previous_pending[catalog_item["name"]])
            scan_log.append({"id": catalog_item["id"], "action": "kept", "reason": reason, "status": schedule_state.get("status", "ok") if schedule_state else "pending", "last_attempt": schedule_state.get("last_attempt", "") if schedule_state else ""})
            continue
        try:
            current = fetch_catalog_item(catalog_item)
            indicators.append(current)
            scan_log.append({"id": catalog_item["id"], "action": "updated", "reason": reason, "status": "ok", "last_attempt": now.date().isoformat()})
        except Exception as exc:  # noqa: BLE001
            if old:
                stale = dict(old)
                stale["status"] = "stale"
                stale["stale_reason"] = "本次扫描失败，保留上次有效值"
                indicators.append(stale)
            else:
                pending.append({
                    "name": catalog_item["name"],
                    "name_en": catalog_item["name_en"],
                    "reason": f"首次扫描未取得有效值：{exc}",
                    "reason_en": f"Initial scan returned no valid value: {exc}",
                })
            errors.append({"source": catalog_item["name"], "error": str(exc)})
            scan_log.append({"id": catalog_item["id"], "action": "failed", "reason": reason, "status": "failed", "last_attempt": now.date().isoformat()})

    annotate_freshness(indicators, now)
    indicators.sort(key=lambda item: (item.get("group", ""), item.get("name", "")))
    dimensions = build_dimensions(indicators)
    combinations = build_combinations(indicators, dimensions)
    analysis_payload, macro_judgement = build_analysis_payload(indicators, pending, now)
    status = "healthy" if not errors else "partial" if indicators else "failed"
    return {
        "meta": {
            "generated_at": now.isoformat(timespec="seconds"),
            "generated_label": now.strftime("%Y-%m-%d %H:%M"),
            "timezone": "Asia/Shanghai",
            "scheduled_time": "18:30",
            "status": status,
            "error_count": len(errors),
            "indicator_count": len(indicators),
            "registered_count": 9 + len(CATALOG),
            "scan_count": sum(1 for item in scan_log if item["action"] in {"updated", "failed"}) + 9,
            "fresh_count": sum(1 for item in indicators if item.get("freshness_status") == "current"),
            "stale_count": sum(1 for item in indicators if item.get("freshness_status") == "stale"),
            "notice": "用于宏观学习与公共政策研究，不构成投资建议。",
        },
        "dimensions": dimensions,
        "indicators": indicators,
        "combinations": combinations,
        "learning_note": build_learning_note(dimensions),
        "errors": errors,
        "pending": pending,
        "scan_log": scan_log,
        "analysis": analysis_payload,
        "macro_judgement": macro_judgement,
    }


def write_outputs(payload: dict[str, Any], public_root: Path) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    SITE_ROOT.mkdir(parents=True, exist_ok=True)
    public_root.mkdir(parents=True, exist_ok=True)
    ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)

    latest_json = json.dumps(payload, ensure_ascii=False, indent=2)
    (DATA_ROOT / "latest.json").write_text(latest_json, encoding="utf-8")
    (PROJECT_ROOT / "data" / "daily_snapshot.json").write_text(latest_json, encoding="utf-8")
    snapshots = DATA_ROOT / "snapshots"
    snapshots.mkdir(exist_ok=True)
    snapshot_name = datetime.now(BEIJING).strftime("%Y-%m-%d_%H%M%S.json")
    (snapshots / snapshot_name).write_text(latest_json, encoding="utf-8")

    analysis_payload = payload["analysis"]
    analysis_outputs = {
        "dimension_scores.json": analysis_payload["dimension_scores"],
        "relation_diagnostics.json": analysis_payload["relation_diagnostics"],
        "detected_divergences.json": analysis_payload["detected_divergences"],
        "daily_macro_payload.json": analysis_payload,
        "macro_judgement.json": payload["macro_judgement"],
    }
    for name, content in analysis_outputs.items():
        (ANALYSIS_ROOT / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    reports_root = PROJECT_ROOT / "outputs"
    reports_root.mkdir(exist_ok=True)
    (reports_root / "daily_macro_report.md").write_text(render_markdown(analysis_payload, payload["macro_judgement"]), encoding="utf-8")

    for target in (SITE_ROOT, public_root):
        assets = target / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WEB_ROOT / "index.html", target / "index.html")
        shutil.copy2(WEB_ROOT / "styles.css", assets / "styles.css")
        shutil.copy2(WEB_ROOT / "app.js", assets / "app.js")
        data_js = "window.MACRO_DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
        (assets / "data.js").write_text(data_js, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the static macro dashboard")
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_ROOT)
    parser.add_argument("--force-all", action="store_true", help="Scan every registered source, ignoring release windows")
    parser.add_argument("--force-ids", default="", help="Comma-separated indicator IDs to scan regardless of release windows")
    args = parser.parse_args()
    force_ids = {item.strip() for item in args.force_ids.split(",") if item.strip()}
    payload = assemble(force_all=args.force_all, force_ids=force_ids)
    write_outputs(payload, args.output.resolve())
    print(json.dumps(payload["meta"], ensure_ascii=False))
    return 0 if payload["meta"]["status"] != "failed" else 2


if __name__ == "__main__":
    sys.exit(main())
