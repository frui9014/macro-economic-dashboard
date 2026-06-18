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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "web"
SITE_ROOT = PROJECT_ROOT / "site"
DATA_ROOT = PROJECT_ROOT / "data" / "processed"
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
        "history": points[-260:],
        "status": "ok",
    }


def get_indicator(indicators: list[dict[str, Any]], indicator_id: str) -> dict[str, Any] | None:
    return next((item for item in indicators if item.get("id") == indicator_id and item.get("status") == "ok"), None)


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


def assemble() -> dict[str, Any]:
    now = datetime.now(BEIJING)
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
        for old in previous.get("indicators", []):
            if old.get("id") not in existing_ids and old.get("status") == "ok":
                stale = dict(old)
                stale["status"] = "stale"
                stale["stale_reason"] = "本次抓取失败，保留上次有效值"
                indicators.append(stale)

    indicators.sort(key=lambda item: (item.get("group", ""), item.get("name", "")))
    dimensions = build_dimensions(indicators)
    combinations = build_combinations(indicators, dimensions)
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
            "notice": "用于宏观学习与公共政策研究，不构成投资建议。",
        },
        "dimensions": dimensions,
        "indicators": indicators,
        "combinations": combinations,
        "learning_note": build_learning_note(dimensions),
        "errors": errors,
        "pending": [
            {"name": "中国 10 年期国债", "reason": "待验证稳定、合规的公开接口"},
            {"name": "中国内部月度宏观", "reason": "第二阶段接入官方发布数据"},
            {"name": "创新升级指标", "reason": "第四阶段接入月度与年度数据"},
        ],
    }


def write_outputs(payload: dict[str, Any], public_root: Path) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    SITE_ROOT.mkdir(parents=True, exist_ok=True)
    public_root.mkdir(parents=True, exist_ok=True)

    latest_json = json.dumps(payload, ensure_ascii=False, indent=2)
    (DATA_ROOT / "latest.json").write_text(latest_json, encoding="utf-8")
    snapshots = DATA_ROOT / "snapshots"
    snapshots.mkdir(exist_ok=True)
    snapshot_name = datetime.now(BEIJING).strftime("%Y-%m-%d_%H%M%S.json")
    (snapshots / snapshot_name).write_text(latest_json, encoding="utf-8")

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
    args = parser.parse_args()
    payload = assemble()
    write_outputs(payload, args.output.resolve())
    print(json.dumps(payload["meta"], ensure_ascii=False))
    return 0 if payload["meta"]["status"] != "failed" else 2


if __name__ == "__main__":
    sys.exit(main())
