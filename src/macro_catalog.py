from __future__ import annotations

import csv
import html as html_lib
import io
import json
import math
import re
import socket
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


socket.setdefaulttimeout(30)


def spec(
    indicator_id: str,
    name: str,
    name_en: str,
    group: str,
    group_en: str,
    frequency: str,
    adapter: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "id": indicator_id,
        "name": name,
        "name_en": name_en,
        "group": group,
        "group_en": group_en,
        "frequency": frequency,
        "adapter": adapter,
        **kwargs,
    }


# 每个原始指标组至少登记一项主序列；组内需要同时判断的指标拆成多项序列。
CATALOG = [
    spec("china10y", "中国 10 年期国债", "China 10Y Government Bond", "中国市场温度", "China Markets", "daily", "bond", unit="%", unit_en="%", source="中债 / AkShare", source_en="ChinaBond / AkShare"),
    spec("china_gdp", "中国实际 GDP 增速", "China Real GDP Growth", "中国内部宏观", "China Macro", "quarterly", "ak", function="macro_china_gdp", date_col="季度", value_col="国内生产总值-同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_months=[1, 4, 7, 10], release_days=list(range(15, 21))),
    spec("china_pmi_man", "中国制造业 PMI", "China Manufacturing PMI", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_pmi", date_col="月份", value_col="制造业-指数", unit="指数点", unit_en="index", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=[28, 29, 30, 31, 1, 2]),
    spec("china_pmi_nonman", "中国非制造业 PMI", "China Non-manufacturing PMI", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_pmi", date_col="月份", value_col="非制造业-指数", unit="指数点", unit_en="index", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=[28, 29, 30, 31, 1, 2]),
    spec("china_industrial", "工业增加值", "Industrial Value Added", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_gyzjz", date_col="月份", value_col="同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(14, 19))),
    spec("china_retail", "社会消费品零售", "Retail Sales", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_consumer_goods_retail", date_col="月份", value_col="同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(14, 19))),
    spec("china_fai", "固定资产投资", "Fixed Asset Investment", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_gdzctz", date_col="月份", value_col="同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(14, 19))),
    spec("china_property", "房地产景气指数", "Real Estate Climate Index", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_real_estate", date_col="日期", value_col="最新值", unit="指数点", unit_en="index", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(14, 19))),
    spec("china_house_price", "70 城新房价格", "70-city New Home Prices", "中国内部宏观", "China Macro", "monthly", "ak_house", function="macro_china_new_house_price", date_col="日期", value_col="新建商品住宅价格指数-同比", unit="指数（上年=100）", unit_en="index (year ago=100)", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(15, 19))),
    spec("china_cpi", "中国 CPI", "China CPI", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_cpi", date_col="月份", value_col="全国-同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(8, 13))),
    spec("china_ppi", "中国 PPI", "China PPI", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_ppi", date_col="月份", value_col="当月同比增长", unit="% 同比", unit_en="% YoY", source="国家统计局 / AkShare", source_en="NBS / AkShare", release_days=list(range(8, 13))),
    spec("china_tsf", "社会融资规模增量", "Total Social Financing Flow", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_shrzgm", date_col="月份", value_col="社会融资规模增量", unit="亿元", unit_en="RMB 100m", source="中国人民银行 / AkShare", source_en="PBOC / AkShare", release_days=list(range(9, 16))),
    spec("china_m2", "M2 增速", "M2 Growth", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_money_supply", date_col="月份", value_col="货币和准货币(M2)-同比增长", unit="% 同比", unit_en="% YoY", source="中国人民银行 / AkShare", source_en="PBOC / AkShare", release_days=list(range(9, 16))),
    spec("china_new_loans", "新增人民币贷款", "New RMB Loans", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_new_financial_credit", date_col="月份", value_col="当月", unit="亿元", unit_en="RMB 100m", source="中国人民银行 / AkShare", source_en="PBOC / AkShare", release_days=list(range(9, 16))),
    spec("china_exports", "中国出口", "China Exports", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_hgjck", date_col="月份", value_col="当月出口额-同比增长", unit="% 同比", unit_en="% YoY", source="海关总署 / AkShare", source_en="GACC / AkShare", release_days=list(range(7, 15))),
    spec("china_imports", "中国进口", "China Imports", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_hgjck", date_col="月份", value_col="当月进口额-同比增长", unit="% 同比", unit_en="% YoY", source="海关总署 / AkShare", source_en="GACC / AkShare", release_days=list(range(7, 15))),
    spec("china_trade_balance", "中国贸易差额", "China Trade Balance", "中国内部宏观", "China Macro", "monthly", "ak", function="macro_china_trade_balance", date_col="日期", value_col="今值", forecast_col="预测值", previous_col="前值", unit="亿美元", unit_en="USD 100m", source="海关总署 / AkShare", source_en="GACC / AkShare", release_days=list(range(7, 15))),
    spec("china_unemployment", "城镇调查失业率", "Surveyed Urban Unemployment", "中国内部宏观", "China Macro", "monthly", "nbs_release", pattern=r"(\d{1,2})\s*月份[^。]{0,30}全国城镇调查失业率为\s*([\d.]+)\s*%", unit="%", unit_en="%", source="国家统计局", source_en="NBS", release_days=list(range(14, 19))),
    spec("us_nonfarm", "美国非农新增就业", "U.S. Nonfarm Payrolls", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "bls", series="CES0000000001", transform="difference", scale=0.1, unit="万人", unit_en="10k jobs", source="美国劳工统计局 BLS", source_en="U.S. BLS", release_days=list(range(1, 11))),
    spec("us_unemployment", "美国失业率", "U.S. Unemployment Rate", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "bls", series="LNS14000000", unit="%", unit_en="%", source="美国劳工统计局 BLS", source_en="U.S. BLS", release_days=list(range(1, 11))),
    spec("us_cpi", "美国 CPI", "U.S. CPI", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "bls", series="CUUR0000SA0", transform="yoy", unit="% 同比", unit_en="% YoY", source="美国劳工统计局 BLS", source_en="U.S. BLS", release_days=list(range(10, 16))),
    spec("us_core_cpi", "美国核心 CPI", "U.S. Core CPI", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "bls", series="CUSR0000SA0L1E", transform="yoy", unit="% 同比", unit_en="% YoY", source="美国劳工统计局 BLS", source_en="U.S. BLS", release_days=list(range(10, 16))),
    spec("us_pce", "美国 PCE 价格指数", "U.S. PCE Price Index", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "fred", series="PCEPI", unit="指数", unit_en="index", source="BEA / FRED", source_en="BEA / FRED", release_days=list(range(25, 32))),
    spec("us_core_pce", "美国核心 PCE", "U.S. Core PCE", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "ak", function="macro_usa_core_pce_price", date_col="日期", value_col="今值", forecast_col="预测值", previous_col="前值", unit="% 同比", unit_en="% YoY", source="BEA / AkShare", source_en="BEA / AkShare", release_days=list(range(25, 32))),
    spec("us_ism_man", "美国 ISM 制造业 PMI", "U.S. ISM Manufacturing PMI", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "ak", function="macro_usa_ism_pmi", date_col="日期", value_col="今值", forecast_col="预测值", previous_col="前值", unit="指数点", unit_en="index", source="ISM / AkShare", source_en="ISM / AkShare", release_days=[1, 2, 3]),
    spec("us_ism_services", "美国 ISM 服务业 PMI", "U.S. ISM Services PMI", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "ak", function="macro_usa_ism_non_pmi", date_col="日期", value_col="今值", forecast_col="预测值", previous_col="前值", unit="指数点", unit_en="index", source="ISM / AkShare", source_en="ISM / AkShare", release_days=[3, 4, 5, 6]),
    spec("oecd_cli", "OECD G20 综合领先指标", "OECD G20 Composite Leading Indicator", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "oecd_cli", unit="指数", unit_en="index", source="OECD SDMX", source_en="OECD SDMX"),
    spec("global_trade", "CPB 全球贸易量", "CPB World Trade Volume", "全球 / 美国基本面", "Global / U.S. Macro", "monthly", "cpb", freshness_limit_days=120, unit="指数（2021=100）", unit_en="index (2021=100)", source="荷兰经济政策分析局 CPB", source_en="CPB Netherlands"),
    spec("china_rd", "中国 R&D 经费强度", "China R&D Intensity", "创新升级", "Innovation", "annual", "worldbank", indicator="GB.XPD.RSDV.GD.ZS", unit="占 GDP %", unit_en="% of GDP", source="世界银行 / 国家统计局", source_en="World Bank / NBS", release_months=[9, 10]),
    spec("china_patents", "中国居民发明专利申请", "China Resident Patent Applications", "创新升级", "Innovation", "annual", "worldbank", indicator="IP.PAT.RESD", unit="件", unit_en="applications", source="世界银行 / WIPO", source_en="World Bank / WIPO"),
    spec("china_hightech_exports", "高技术产品出口占比", "High-tech Export Share", "创新升级", "Innovation", "annual", "worldbank", indicator="TX.VAL.TECH.MF.ZS", unit="制成品出口 %", unit_en="% of manufactured exports", source="世界银行 / 海关总署", source_en="World Bank / GACC"),
    spec("china_hightech_output", "高技术制造业增加值", "High-tech Manufacturing Output", "创新升级", "Innovation", "monthly", "nbs_release", pattern=r"高技术制造业增加值(?:同比)?增长\s*([\d.]+)\s*%", unit="% 同比", unit_en="% YoY", source="国家统计局", source_en="NBS", release_days=list(range(14, 19))),
    spec("china_hightech_investment", "高技术产业投资", "High-tech Industry Investment", "创新升级", "Innovation", "monthly", "nbs_release", pattern=r"高技术产业投资同比增长\s*([\d.]+)\s*%", unit="% 累计同比", unit_en="% YTD YoY", source="国家统计局", source_en="NBS", release_days=list(range(14, 19))),
]


def should_scan(item: dict[str, Any], now: datetime, previous: dict[str, Any] | None, force: bool = False) -> tuple[bool, str]:
    if force or previous is None:
        return True, "initial_or_forced"
    if previous.get("status") in {"failed", "pending"}:
        if previous.get("last_attempt") == now.date().isoformat():
            return False, "same_day_failure_backoff"
        return True, "retry_after_failure"
    if item["frequency"] == "daily":
        return True, "daily"
    if item["frequency"] in {"monthly", "quarterly"} and now.day == 1 and now.month in {1, 4, 7, 10}:
        return True, "quarterly_revision_audit"
    months = item.get("release_months")
    days = item.get("release_days")
    if months and now.month not in months:
        return False, "outside_release_month"
    if days:
        return (now.day in days, "release_window" if now.day in days else "outside_release_window")
    return True, "unknown_calendar_daily_check"


def period_key(value: Any) -> tuple[int, int, int]:
    text = str(value)
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if len(nums) >= 3 and nums[0] > 1900:
        return nums[0], nums[1], nums[2]
    if len(nums) >= 2 and nums[0] > 1900:
        return nums[0], nums[1], 1
    if len(nums) == 1:
        n = nums[0]
        if n >= 100000:
            return n // 100, n % 100, 1
        if n > 1900:
            return n, 12, 31
    return 0, 0, 0


def valid_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def normalize_rows(rows: list[tuple[Any, Any]], limit: int = 60) -> list[dict[str, Any]]:
    clean = [(date, float(value)) for date, value in rows if valid_number(value)]
    clean.sort(key=lambda row: period_key(row[0]))
    return [{"date": str(date), "value": round(value, 6)} for date, value in clean[-limit:]]


def low_frequency_result(item: dict[str, Any], history: list[dict[str, Any]], forecast: Any = None, reported_previous: Any = None) -> dict[str, Any]:
    if not history:
        raise ValueError("no valid observations")
    latest = history[-1]
    previous = history[-2]["value"] if len(history) > 1 else None
    result = {
        **{key: item[key] for key in ("id", "name", "name_en", "group", "group_en", "frequency", "unit", "unit_en", "source", "source_en")},
        "value": latest["value"],
        "date": latest["date"],
        "previous_value": float(reported_previous) if valid_number(reported_previous) else previous,
        "forecast": float(forecast) if valid_number(forecast) else None,
        "decimals": 2,
        "history": history,
        "status": "ok",
        "source_url": item.get("source_url", "#"),
    }
    if item.get("freshness_limit_days") is not None:
        result["freshness_limit_days"] = int(item["freshness_limit_days"])
    return result


_AK_CACHE: dict[str, Any] = {}


def fetch_ak(item: dict[str, Any]) -> dict[str, Any]:
    import akshare as ak

    function_name = item["function"]
    if function_name not in _AK_CACHE:
        _AK_CACHE[function_name] = getattr(ak, function_name)()
    frame = _AK_CACHE[function_name]
    if item["date_col"] not in frame or item["value_col"] not in frame:
        raise KeyError(f"missing columns: {item['date_col']} / {item['value_col']}")
    if item["adapter"] == "ak_house":
        usable = frame[[item["date_col"], item["value_col"]]].copy()
        usable[item["value_col"]] = usable[item["value_col"]].apply(lambda value: float(value) if valid_number(value) else None)
        grouped = usable.dropna().groupby(item["date_col"])[item["value_col"]].mean()
        history = normalize_rows(list(grouped.items()))
        return low_frequency_result(item, history)
    history = normalize_rows(list(zip(frame[item["date_col"]], frame[item["value_col"]])))
    if not history:
        raise ValueError("source returned no non-null observation")
    latest_key = period_key(history[-1]["date"])
    matched = frame[frame[item["date_col"]].apply(period_key) == latest_key]
    row = matched.iloc[-1] if not matched.empty else frame.iloc[-1]
    forecast = row.get(item.get("forecast_col")) if item.get("forecast_col") else None
    reported_previous = row.get(item.get("previous_col")) if item.get("previous_col") else None
    return low_frequency_result(item, history, forecast, reported_previous)


def fetch_fred(item: dict[str, Any]) -> dict[str, Any]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={item['series']}"
    request = urllib.request.Request(url, headers={"User-Agent": "MacroEconomicObservatory/0.2"})
    with urllib.request.urlopen(request, timeout=20) as response:
        reader = csv.DictReader(io.StringIO(response.read().decode("utf-8")))
        history = normalize_rows([(row["observation_date"], row[item["series"]]) for row in reader])
    result = low_frequency_result(item, history)
    result["source_url"] = url
    return result


def fetch_worldbank(item: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.worldbank.org/v2/country/CHN/indicator/{item['indicator']}?format=json&per_page=100"
    request = urllib.request.Request(url, headers={"User-Agent": "MacroEconomicObservatory/0.2"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    history = normalize_rows([(row.get("date"), row.get("value")) for row in rows])
    result = low_frequency_result(item, history)
    result["source_url"] = url
    return result


def fetch_bls(item: dict[str, Any]) -> dict[str, Any]:
    year = datetime.now().year
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    body = json.dumps({"seriesid": [item["series"]], "startyear": str(year - 4), "endyear": str(year)}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    series = payload.get("Results", {}).get("series", [])
    if not series:
        raise ValueError("BLS returned no series")
    raw = []
    for row in series[0].get("data", []):
        period = row.get("period", "")
        if not period.startswith("M") or period == "M13" or not valid_number(row.get("value")):
            continue
        raw.append((f"{row['year']}-{period[1:]}-01", float(row["value"])))
    raw.sort(key=lambda row: period_key(row[0]))
    transform = item.get("transform")
    if transform == "difference":
        scale = float(item.get("scale", 1))
        raw = [(raw[i][0], (raw[i][1] - raw[i - 1][1]) * scale) for i in range(1, len(raw))]
    elif transform == "yoy":
        raw = [(raw[i][0], (raw[i][1] / raw[i - 12][1] - 1) * 100) for i in range(12, len(raw)) if raw[i - 12][1]]
    result = low_frequency_result(item, normalize_rows(raw))
    result["source_url"] = url
    return result


def fetch_oecd_cli(item: dict[str, Any]) -> dict[str, Any]:
    url = "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.STES,DSD_STES@DF_CLI,4.1/G20.M.LI.IX._Z.AA.IX._Z.H?startPeriod=2018-01"
    request = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": "MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        reader = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig")))
        history = normalize_rows([(row.get("TIME_PERIOD"), row.get("OBS_VALUE")) for row in reader])
    result = low_frequency_result(item, history)
    result["source_url"] = url
    return result


def _xlsx_cells(payload: bytes, sheet: str = "xl/worksheets/sheet1.xml") -> dict[str, Any]:
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(payload)) as workbook:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", namespace)) for item in root.findall("m:si", namespace)]
        root = ET.fromstring(workbook.read(sheet))
    cells: dict[str, Any] = {}
    for cell in root.findall(".//m:c", namespace):
        reference = cell.get("r", "")
        value = cell.find("m:v", namespace)
        if not reference or value is None or value.text is None:
            continue
        raw: Any = value.text
        if cell.get("t") == "s":
            raw = shared[int(raw)]
        cells[reference] = raw
    return cells


def fetch_cpb(item: dict[str, Any]) -> dict[str, Any]:
    page_url = "https://www.cpb.nl/en/worldtrademonitor/latest"
    request = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0 MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    match = re.search(r'href="([^"]*cpb-world-trade-monitor-[^"]+\.xlsx)"', html, re.IGNORECASE)
    if not match:
        raise ValueError("CPB latest page contains no World Trade Monitor workbook")
    workbook_url = urllib.parse.urljoin(page_url, match.group(1))
    request = urllib.request.Request(workbook_url, headers={"User-Agent": "Mozilla/5.0 MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=45) as response:
        cells = _xlsx_cells(response.read())
    rows: list[tuple[str, Any]] = []
    for column in range(6, 500):
        letters = ""
        number = column
        while number:
            number, remainder = divmod(number - 1, 26)
            letters = chr(65 + remainder) + letters
        period = str(cells.get(f"{letters}4", ""))
        value = cells.get(f"{letters}8")
        matched_period = re.fullmatch(r"(\d{4})m(\d{2})", period)
        if matched_period and valid_number(value):
            rows.append((f"{matched_period.group(1)}-{matched_period.group(2)}-01", value))
    result = low_frequency_result(item, normalize_rows(rows))
    result["source_url"] = workbook_url
    return result


def fetch_nbs_release(item: dict[str, Any]) -> dict[str, Any]:
    index_url = "https://www.stats.gov.cn/sj/zxfb/"
    request = urllib.request.Request(index_url, headers={"User-Agent": "Mozilla/5.0 MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        index_html = response.read().decode("utf-8", errors="replace")
    match = re.search(r'href="([^"]+)"[^>]+title=[\'\"][^\'\"]*月份国民经济运行', index_html)
    if not match:
        raise ValueError("NBS release index contains no monthly national-economy release")
    release_url = urllib.parse.urljoin(index_url, match.group(1))
    request = urllib.request.Request(release_url, headers={"User-Agent": "Mozilla/5.0 MacroEconomicObservatory/0.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        release_html = response.read().decode("utf-8", errors="replace")
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", release_html))
    text = re.sub(r"\s+", " ", text)
    value_match = re.search(item["pattern"], text)
    if not value_match:
        raise ValueError(f"NBS release does not contain {item['name']}")
    period_match = re.search(r"/(\d{4})(\d{2})/t\d+_", release_url)
    year = int(period_match.group(1)) if period_match else datetime.now().year
    if item["id"] == "china_unemployment":
        month, value = int(value_match.group(1)), value_match.group(2)
    else:
        headline_month = re.search(r"(\d{1,2})月份国民经济运行", text)
        month = int(headline_month.group(1)) if headline_month else max(1, int(period_match.group(2)) - 1) if period_match else datetime.now().month
        value = value_match.group(1)
    result = low_frequency_result(item, normalize_rows([(f"{year}-{month:02d}-01", value)]))
    result["source_url"] = release_url
    return result


def fetch_catalog_item(item: dict[str, Any]) -> dict[str, Any]:
    if item["adapter"] in {"ak", "ak_house"}:
        return fetch_ak(item)
    if item["adapter"] == "fred":
        return fetch_fred(item)
    if item["adapter"] == "worldbank":
        return fetch_worldbank(item)
    if item["adapter"] == "bls":
        return fetch_bls(item)
    if item["adapter"] == "oecd_cli":
        return fetch_oecd_cli(item)
    if item["adapter"] == "cpb":
        return fetch_cpb(item)
    if item["adapter"] == "nbs_release":
        return fetch_nbs_release(item)
    if item["adapter"] == "bond":
        import akshare as ak

        frame = ak.bond_zh_us_rate(start_date="20200101")
        history = normalize_rows(list(zip(frame["日期"], frame["中国国债收益率10年"])), limit=260)
        return low_frequency_result(item, history)
    raise RuntimeError("official machine-readable adapter not yet available")
