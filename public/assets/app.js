(function () {
  "use strict";

  const data = window.MACRO_DASHBOARD_DATA;
  if (!data) {
    document.body.innerHTML = "<p style='padding:2rem;font-family:sans-serif'>Data file missing / 数据文件缺失</p>";
    return;
  }

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  let rangeDays = 30;
  let language = localStorage.getItem("macro-language") === "en" ? "en" : "zh";

  const UI = {
    zh: {
      title: "宏观经济观察", tabToday: "当日数据", tabTrends: "时间变化", todayView: "今日总判断",
      dimensions: "八维状态", dimensionsHint: "市场信号与宏观事实分层展示", thermometer: "今日温度计",
      thermometerHint: "点击指标查看可能原因与后果", combinations: "组合观察", combinationsHint: "共振比单一指标更重要",
      learningNote: "宏观学习笔记", indicator: "指标", range7: "7日", range30: "1月", range90: "3月", range365: "1年",
      pending: "待接入数据", pendingHint: "缺失不会被伪造或静默填充", schedule: "当前为按需手动更新",
      updated: "更新于", beijing: "北京时间", source: "来源", frequency: "日频", confidence: "置信度", daily: "日", day5: "5日", day20: "20日", previous: "前值", forecast: "预期", fresh: "最新", staleData: "陈旧", unknownFreshness: "日期未知",
      reason: "可能原因", consequence: "可能后果", stale: "保留上次有效值", latestMove: "最新日变动", intervalMove: "区间变化",
      intervalRange: "区间范围", insufficient: "历史观测不足。", noErrors: (n) => `共更新 ${n} 项日频序列；低频指标只在发布日进入当日页。`,
      errors: (n) => `${n} 个数据源本次扫描未取得新值；已有数据保持不变。`, notice: "用于宏观学习与公共政策研究，不构成投资建议。"
    },
    en: {
      title: "Macro Observatory", tabToday: "Today", tabTrends: "Trends", todayView: "Today’s Macro View",
      dimensions: "Eight Dimensions", dimensionsHint: "Market signals separated from macro facts", thermometer: "Daily Indicators",
      thermometerHint: "Open a card for possible drivers and implications", combinations: "Combined Signals", combinationsHint: "Co-movement matters more than one series",
      learningNote: "Macro Learning Note", indicator: "Indicator", range7: "7D", range30: "1M", range90: "3M", range365: "1Y",
      pending: "Pending Data", pendingHint: "Missing observations are never fabricated or silently filled", schedule: "Currently updated manually on request",
      updated: "Updated", beijing: "Beijing time", source: "Source", frequency: "Daily", confidence: "Confidence", daily: "1D", day5: "5D", day20: "20D", previous: "Previous", forecast: "Forecast", fresh: "Current", staleData: "Stale", unknownFreshness: "Date unknown",
      reason: "Possible driver", consequence: "Possible implication", stale: "Last valid value retained", latestMove: "Latest daily move", intervalMove: "Period change",
      intervalRange: "Range", insufficient: "Insufficient history.", noErrors: (n) => `${n} daily series updated; lower-frequency data appear only on release days.`,
      errors: (n) => `${n} source(s) failed in this run; last valid values were retained.`, notice: "For macro learning and public-policy research; not investment advice."
    }
  };

  const INDICATORS = {
    us2y: { zh: ["美国 2 年期国债", "全球利率", "美国财政部", "%", "美国国债收益率是全球资产定价和美元金融条件的重要锚。", "若持续上行，融资成本和风险资产估值压力可能增加。", "若持续回落，全球金融条件可能边际缓和，但也可能反映增长担忧。"], en: ["U.S. 2Y Treasury", "Global Rates", "U.S. Treasury", "%", "Treasury yields anchor global asset pricing and dollar financial conditions.", "If sustained, higher yields may raise financing costs and pressure risk-asset valuations.", "If sustained, lower yields may ease financial conditions, but can also reflect growth concerns."] },
    us10y: { zh: ["美国 10 年期国债", "全球利率", "美国财政部", "%", "美国国债收益率是全球资产定价和美元金融条件的重要锚。", "若持续上行，融资成本和风险资产估值压力可能增加。", "若持续回落，全球金融条件可能边际缓和，但也可能反映增长担忧。"], en: ["U.S. 10Y Treasury", "Global Rates", "U.S. Treasury", "%", "Treasury yields anchor global asset pricing and dollar financial conditions.", "If sustained, higher yields may raise financing costs and pressure risk-asset valuations.", "If sustained, lower yields may ease financial conditions, but can also reflect growth concerns."] },
    dxy: { zh: ["美元指数", "全球市场", "Yahoo / ICE", "点", "美元走强通常收紧非美经济体的金融条件。", "若持续走强，人民币与新兴市场资产通常面临更大外部压力。", "若持续回落，非美资产和跨境流动性压力可能缓解。"], en: ["U.S. Dollar Index", "Global Markets", "Yahoo / ICE", "pts", "A stronger dollar typically tightens financial conditions outside the United States.", "If sustained, RMB and emerging-market assets may face greater external pressure.", "If sustained, pressure on non-U.S. assets and cross-border liquidity may ease."] },
    vix: { zh: ["VIX", "全球市场", "Yahoo / CBOE", "点", "VIX 反映美股期权隐含波动和全球避险温度。", "若持续上升，风险资产估值与跨境风险偏好可能承压。", "若持续下降，通常意味着市场风险偏好趋于稳定。"], en: ["VIX", "Global Markets", "Yahoo / CBOE", "pts", "VIX captures implied U.S. equity volatility and global risk aversion.", "If sustained, risk-asset valuations and cross-border risk appetite may weaken.", "If sustained, declining volatility usually signals more stable risk appetite."] },
    brent: { zh: ["Brent 原油", "全球市场", "Yahoo / ICE", "美元/桶", "油价同时受全球需求、供给约束和地缘事件影响。", "若持续上升，能源通胀和企业成本压力可能增加。", "若持续下降，通胀压力可能缓解，但也需排查需求走弱。"], en: ["Brent Crude", "Global Markets", "Yahoo / ICE", "USD/bbl", "Oil reflects global demand, supply constraints, and geopolitical events.", "If sustained, energy inflation and business cost pressures may rise.", "If sustained, inflation pressure may ease, though weaker demand should also be checked."] },
    copper: { zh: ["铜", "全球市场", "Yahoo / COMEX", "美分/磅", "铜价常被用于观察全球制造业与基建需求预期。", "若需求因素主导，持续上行可能预示制造业预期改善。", "若持续回落，可能提示全球工业需求预期转弱。"], en: ["Copper", "Global Markets", "Yahoo / COMEX", "¢/lb", "Copper is a high-frequency proxy for global manufacturing and infrastructure demand.", "If demand-led and sustained, gains may signal improving manufacturing expectations.", "Persistent declines may point to softer global industrial-demand expectations."] },
    usdcny: { zh: ["USD/CNY", "中国市场", "Yahoo / 外汇行情", "人民币/美元", "数值上升表示人民币对美元走弱，需结合美元指数共同判断。", "若与美元同步走强，外部金融约束可能加大。", "若持续回落，人民币外部压力可能缓解。"], en: ["USD/CNY", "China Markets", "Yahoo / FX", "CNY/USD", "A rise means RMB depreciation against the dollar and should be read with DXY.", "If it rises with the dollar, external financial constraints may intensify.", "If sustained, a decline may indicate easing external pressure on the RMB."] },
    csi300: { zh: ["沪深 300", "中国市场", "Yahoo / 中证指数", "点", "反映大型 A 股公司的市场表现和国内政策、增长预期。", "若与信用和基本面共振，可能意味着增长预期改善。", "若持续回落，可能反映风险偏好或增长预期承压。"], en: ["CSI 300", "China Markets", "Yahoo / CSI", "pts", "Tracks large-cap A shares and domestic policy and growth expectations.", "If confirmed by credit and activity data, gains may signal improving growth expectations.", "Persistent declines may reflect weaker risk appetite or growth expectations."] },
    hsi: { zh: ["恒生指数", "中国市场", "Yahoo / 恒生指数", "点", "同时受中国增长预期和全球美元流动性影响。", "若与 A 股同步走强，市场对中国资产的预期可能改善。", "若弱于 A 股，全球流动性或离岸风险偏好可能构成额外压力。"], en: ["Hang Seng Index", "China Markets", "Yahoo / Hang Seng", "pts", "Reflects both China growth expectations and global dollar liquidity.", "If it rises with A shares, expectations for Chinese assets may be improving.", "If it underperforms A shares, global liquidity or offshore risk appetite may be an added drag."] }
  };

  const PRIORITY_GROUPS = [
    { zh: "中国内部宏观", en: "China Macro", groups: [
      ["china_gdp"],
      ["china_pmi_man", "china_pmi_nonman", "china_pmi_composite"],
      ["china_industrial"],
      ["china_retail"],
      ["china_fai", "china_fai_manufacturing", "china_fai_infrastructure", "china_fai_property"],
      ["china_property", "china_house_price", "china_property_sales", "china_property_starts", "china_property_investment"],
      ["china_cpi"],
      ["china_ppi"],
      ["china_tsf", "china_m2", "china_new_loans"],
      ["china_exports", "china_imports", "china_trade_balance"],
      ["china_unemployment", "china_youth_unemployment"],
    ]},
    { zh: "中国市场温度", en: "China Market Temperature", groups: [
      ["china10y"],
      ["usdcny", "cfets_rmb"],
      ["csi300", "hsi", "hscei"],
    ]},
    { zh: "全球 / 美国基本面", en: "Global / U.S. Macro", groups: [
      ["us_nonfarm", "us_unemployment"],
      ["us_cpi", "us_core_cpi", "us_pce", "us_core_pce"],
      ["us_ism_man", "us_ism_services"],
      ["us10y", "us2y"],
      ["dxy"],
      ["oecd_cli", "global_trade"],
    ]},
    { zh: "全球市场温度", en: "Global Market Temperature", groups: [
      ["brent", "wti"],
      ["copper"],
      ["vix"],
    ]},
    { zh: "创新升级", en: "Innovation & Upgrading", groups: [
      ["china_rd"],
      ["china_hightech_output", "china_hightech_investment"],
      ["china_patents", "china_pct_patents", "china_triadic_patents"],
      ["china_hightech_exports", "china_mechanical_exports"],
    ]},
  ];
  const PRIORITY = new Map();
  const SECTION = new Map();
  let priorityPosition = 0;
  PRIORITY_GROUPS.forEach((section, sectionIndex) => {
    section.groups.forEach((ids, groupIndex) => {
      ids.forEach((id, itemIndex) => {
        PRIORITY.set(id, priorityPosition + itemIndex / 100);
        SECTION.set(id, { zh: section.zh, en: section.en, sectionIndex, groupIndex });
      });
      priorityPosition += 1;
    });
  });
  function priorityRank(item) { return PRIORITY.has(item.id) ? PRIORITY.get(item.id) : 10000; }

  const DIMENSION_NAMES = { "全球流动性": "Global Liquidity", "全球需求": "Global Demand", "中国增长": "China Growth", "中国内需": "China Domestic Demand", "中国地产": "China Property", "中国信用": "China Credit", "通胀压力": "Inflation Pressure", "创新升级": "Innovation & Upgrading" };
  const TERMS = { "收紧": "Tightening", "宽松": "Easing", "中性": "Neutral", "上行": "Rising", "下行": "Falling", "平稳": "Stable", "预期改善": "Expectations Improving", "预期承压": "Expectations Under Pressure", "预期平稳": "Expectations Stable", "待宏观数据": "Awaiting Macro Data", "待结构数据": "Awaiting Structural Data", "市场压力上升": "Market Pressure Rising", "市场压力下降": "Market Pressure Falling", "稳定": "Stable", "中": "Medium", "低": "Low", "日频市场信号": "Daily market signals", "大宗商品代理": "Commodity proxies", "仅市场预期": "Market expectations only", "月度": "Monthly", "能源市场代理": "Energy-market proxy", "月度/年度": "Monthly / annual", "—": "—", "同向": "Aligned", "分化": "Divergent", "外部压力同向": "External Pressure Aligned", "联动分化": "Linkage Divergent", "外部压力缓和": "External Pressure Easing" };

  function escapeHtml(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
  function t(key) { return UI[language][key]; }
  function term(value) { return language === "en" ? (TERMS[value] || value) : value; }
  function meta(item) {
    if (INDICATORS[item.id]) return INDICATORS[item.id][language];
    if (language === "en") return [item.name_en || item.name, item.group_en || item.group, item.source_en || item.source, item.unit_en || item.unit, item.reason_en || "Latest available observation retained according to its release cycle.", item.consequence_en || "Interpret with related indicators; one release does not establish a trend.", item.consequence_en || "Interpret with related indicators; one release does not establish a trend."];
    return [item.name, item.group, item.source, item.unit, item.reason || "按该指标发布周期保留最新一期有效值。", item.consequence || "需与相关指标组合判断，单期数据不代表趋势。", item.consequence || "需与相关指标组合判断，单期数据不代表趋势。"];
  }
  function frequencyLabel(item) { const labels = { zh: { daily: "日频", weekly: "周频", monthly: "月度", quarterly: "季度", annual: "年度" }, en: { daily: "Daily", weekly: "Weekly", monthly: "Monthly", quarterly: "Quarterly", annual: "Annual" } }; return labels[language][item.frequency || "daily"] || item.frequency; }
  function displayName(item) { return meta(item)[0]; }
  function displayGroup(item) { const section = SECTION.get(item.id); return section ? section[language] : meta(item)[1]; }
  function displaySource(item) { return meta(item)[2]; }
  function displayUnit(item) { return meta(item)[3]; }

  function formatValue(item) { return Number(item.value).toLocaleString(language === "en" ? "en-US" : "zh-CN", { minimumFractionDigits: item.decimals, maximumFractionDigits: item.decimals }); }
  function formatMove(value, unit) { if (value == null || Number.isNaN(value)) return "—"; return `${value > 0 ? "+" : ""}${Number(value).toFixed(unit === "bp" ? 1 : 2)}${unit}`; }
  function moveClass(value) { return value > 0 ? "positive" : value < 0 ? "negative" : ""; }
  function dimensionName(value) { return language === "en" ? (DIMENSION_NAMES[value] || value) : value; }

  function initTabs() {
    const activate = (name) => { $$(".tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === name)); $$(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === name)); if (name === "trends") renderTrend(); };
    $$(".tab").forEach((button) => button.addEventListener("click", () => { window.location.hash = button.dataset.tab; activate(button.dataset.tab); }));
    if (window.location.hash === "#trends") activate("trends");
  }

  function renderMeta() {
    $("#update-time").textContent = `${t("updated")} ${data.meta.generated_label} · ${t("beijing")}`;
    $("#health-dot").className = `health-dot ${data.meta.status}`;
    const freshnessText = language === "zh" ? `${data.meta.fresh_count ?? data.meta.indicator_count} 项最新 · ${data.meta.stale_count || 0} 项陈旧` : `${data.meta.fresh_count ?? data.meta.indicator_count} current · ${data.meta.stale_count || 0} stale`;
    $("#data-notice").textContent = `${freshnessText}${data.meta.error_count ? ` · ${t("errors")(data.meta.error_count)}` : ""}`;
    $("#footer-notice").textContent = t("notice");
  }

  function renderSummary() {
    const map = Object.fromEntries(data.dimensions.map((item) => [item.name, item.status]));
    $("#daily-summary").textContent = language === "zh"
      ? `全球流动性${map["全球流动性"]}，全球需求${map["全球需求"]}；中国资产${map["中国增长"]}，通胀${map["通胀压力"]}。`
      : `Global liquidity is ${term(map["全球流动性"]).toLowerCase()} and global demand is ${term(map["全球需求"]).toLowerCase()}; China asset expectations are ${term(map["中国增长"]).toLowerCase()}, while inflation pressure is ${term(map["通胀压力"]).toLowerCase()}.`;
  }

  function renderDimensions() {
    $("#dimensions").innerHTML = data.dimensions.map((item) => `<article class="dimension"><span class="dimension-name">${escapeHtml(dimensionName(item.name))}</span><strong class="dimension-status">${escapeHtml(term(item.status))}</strong><span class="dimension-meta">${t("confidence")} ${escapeHtml(term(item.confidence))} · ${escapeHtml(term(item.freshness))}</span></article>`).join("");
  }

  function renderIndicators() {
    const groups = {};
    [...data.indicators].sort((a, b) => priorityRank(a) - priorityRank(b)).forEach((item) => { (groups[displayGroup(item)] ||= []).push(item); });
    $("#indicator-groups").innerHTML = Object.entries(groups).map(([name, items]) => `<div class="group-block"><h4 class="group-title">${escapeHtml(name)}</h4><div class="indicator-grid">${items.map((item) => {
      const m = meta(item); const consequence = item.direction === "up" ? m[5] : item.direction === "down" ? m[6] : (language === "zh" ? "当前变化较小，暂不足以单独改变宏观判断。" : "The move is too small to alter the macro view on its own.");
      const isDaily = (item.frequency || "daily") === "daily";
      const changes = isDaily
        ? `<div class="moves"><span>${t("daily")} <b class="${moveClass(item.day_change)}">${formatMove(item.day_change, item.change_unit)}</b></span><span>${t("day5")} <b class="${moveClass(item.five_change)}">${formatMove(item.five_change, item.change_unit)}</b></span><span>${t("day20")} <b class="${moveClass(item.twenty_change)}">${formatMove(item.twenty_change, item.change_unit)}</b></span></div>`
        : `<div class="moves"><span>${t("previous")} <b>${item.previous_value == null ? "—" : Number(item.previous_value).toLocaleString(language === "en" ? "en-US" : "zh-CN")}</b></span>${item.forecast == null ? "" : `<span>${t("forecast")} <b>${Number(item.forecast).toLocaleString(language === "en" ? "en-US" : "zh-CN")}</b></span>`}</div>`;
      const freshness = item.freshness_status || "current";
      const freshnessLabel = freshness === "current" ? t("fresh") : freshness === "stale" ? t("staleData") : t("unknownFreshness");
      return `<details class="indicator ${isDaily ? "daily" : "low-frequency"} freshness-${freshness}"><summary><div class="indicator-top"><span><span class="indicator-name">${escapeHtml(m[0])}</span><span class="indicator-meta">${escapeHtml(m[2])} · ${frequencyLabel(item)}</span></span><span class="indicator-date">${escapeHtml(item.date)}<i class="freshness-badge ${freshness}">${freshnessLabel}</i></span></div><div class="indicator-value">${formatValue(item)}<span class="unit">${escapeHtml(m[3])}</span></div>${changes}${item.status === "stale" ? `<span class="stale-badge">${t("stale")}</span>` : ""}</summary><div class="indicator-detail"><p><strong>${t("reason")}：</strong>${escapeHtml(m[4])}</p><p><strong>${t("consequence")}：</strong>${escapeHtml(consequence)}</p><p><a class="source-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">${t("source")} · ${escapeHtml(m[2])}</a></p></div></details>`;
    }).join("")}</div></div>`).join("");
  }

  const COMBO_EN = {
    "全球金融条件": ["Global Financial Conditions", "Based on co-movement or divergence among the U.S. 10-year yield, dollar, and VIX. It describes market conditions, not the Federal Reserve stance."],
    "美元—人民币联动": ["Dollar–RMB Linkage", "When DXY and USD/CNY rise together, RMB weakness is more likely to include a global-dollar component. Divergence points to China-specific expectations or capital-flow factors."],
    "中国资产共振": ["China Asset Co-movement", "Aligned A-share and Hong Kong moves provide a more consistent policy or growth-expectation signal. Divergence calls for separating domestic factors from global liquidity."],
    "全球需求温度": ["Global Demand Temperature", "Copper and oil offer high-frequency demand clues, but supply and geopolitical forces also move prices; trade and survey data must confirm the signal."]
  };
  function renderCombinations() {
    $("#combinations").innerHTML = data.combinations.map((item) => { const en = COMBO_EN[item.title]; return `<article class="combination"><div class="combination-head"><h4>${escapeHtml(language === "en" && en ? en[0] : item.title)}</h4><span class="signal">${escapeHtml(term(item.signal))}</span></div><p>${escapeHtml(language === "en" && en ? en[1] : item.analysis)}</p></article>`; }).join("");
    $("#learning-note").textContent = learningNote();
  }

  function learningNote() {
    if (language === "zh") return data.learning_note;
    const status = data.dimensions.find((item) => item.name === "全球流动性")?.status;
    if (status === "收紧") return "Global financial conditions look tighter today. If yields, the dollar, and volatility continue rising together, they can raise financing costs, compress valuations, and pressure emerging-market currencies. One day is not a trend; watch whether the co-movement lasts for at least a week.";
    if (status === "宽松") return "The market mix points to marginally easier global financial conditions. Falling yields, dollar, and volatility often support risk assets and non-U.S. currencies, but the key question is whether this reflects easing inflation or growth fears and expected rate cuts.";
    return "Global financial-condition signals are mixed today. Divergence matters: markets have not settled on one macro narrative, so no single price move should define the outlook. Watch whether yields, the dollar, and volatility form a persistent joint signal.";
  }

  const PENDING_EN = { "中国 10 年期国债": ["China 10Y Government Bond", "Stable, compliant public interface under review"], "中国内部月度宏观": ["China Monthly Macro", "Official releases planned for phase two"], "创新升级指标": ["Innovation & Upgrading", "Monthly and annual series planned for phase four"] };
  function renderSelectAndPending() {
    const select = $("#indicator-select"); const chosen = select.value;
    select.innerHTML = [...data.indicators].filter((item) => item.history?.length).sort((a, b) => priorityRank(a) - priorityRank(b)).map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(displayName(item))}</option>`).join("");
    if ([...select.options].some((option) => option.value === chosen)) select.value = chosen;
    $("#pending").innerHTML = data.pending.map((item) => { const en = PENDING_EN[item.name]; const name = language === "en" ? (item.name_en || en?.[0] || item.name) : item.name; const reason = language === "en" ? (item.reason_en || en?.[1] || item.reason) : item.reason; return `<div class="pending-item"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(reason)}</span></div>`; }).join("");
  }

  function initTrendControls() {
    $("#indicator-select").addEventListener("change", renderTrend);
    $$(".range-switch button").forEach((button) => button.addEventListener("click", () => { $$(".range-switch button").forEach((item) => item.classList.remove("active")); button.classList.add("active"); rangeDays = Number(button.dataset.days); renderTrend(); }));
  }

  function renderTrend() {
    const item = data.indicators.find((indicator) => indicator.id === $("#indicator-select").value); if (!item) return;
    const points = item.history.slice(-rangeDays); $("#trend-name").textContent = displayName(item); $("#trend-value").innerHTML = `${formatValue(item)} <span class="unit">${escapeHtml(displayUnit(item))}</span>`;
    $("#trend-change").className = `trend-change ${moveClass(item.day_change)}`; $("#trend-change").textContent = `${t("latestMove")} ${formatMove(item.day_change, item.change_unit)}`; drawChart(points, item.decimals);
    const values = points.map((point) => point.value); const low = Math.min(...values); const high = Math.max(...values); const intervalMove = pct(values.at(-1), values[0]);
    $("#trend-details").innerHTML = `<div class="trend-detail"><span>${t("intervalMove")}</span><strong class="${moveClass(intervalMove)}">${formatMove(intervalMove, "%")}</strong></div><div class="trend-detail"><span>${t("intervalRange")}</span><strong>${low.toFixed(item.decimals)} — ${high.toFixed(item.decimals)}</strong></div><div class="trend-detail"><span>${t("source")} · ${frequencyLabel(item)}</span><strong>${escapeHtml(displaySource(item))}</strong></div>`;
  }

  function pct(current, previous) { return previous ? (current / previous - 1) * 100 : null; }
  function drawChart(points, decimals) {
    const chart = $("#chart"); if (points.length < 2) { chart.innerHTML = `<p class="muted">${t("insufficient")}</p>`; return; }
    const width = 1000, height = 330, pad = { top: 20, right: 20, bottom: 30, left: 55 }; const values = points.map((point) => point.value); let min = Math.min(...values), max = Math.max(...values); const spread = max - min || Math.abs(max) * .02 || 1; min -= spread * .12; max += spread * .12;
    const x = (index) => pad.left + index * (width - pad.left - pad.right) / (points.length - 1); const y = (value) => pad.top + (max - value) * (height - pad.top - pad.bottom) / (max - min);
    const line = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`).join(" "); const area = `${line} L${x(points.length - 1)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z`;
    const ticks = [0, .25, .5, .75, 1].map((ratio) => { const value = min + (max - min) * ratio, yy = y(value); return `<line class="chart-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${yy}" y2="${yy}"/><text class="chart-label" x="${pad.left - 8}" y="${yy + 3}" text-anchor="end">${value.toFixed(decimals)}</text>`; }).join("");
    chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#175c45" stop-opacity=".16"/><stop offset="1" stop-color="#175c45" stop-opacity="0"/></linearGradient></defs>${ticks}<path class="chart-area" d="${area}"/><path class="chart-line" d="${line}"/><text class="chart-label" x="${pad.left}" y="${height - 8}">${escapeHtml(points[0].date)}</text><text class="chart-label" x="${width - pad.right}" y="${height - 8}" text-anchor="end">${escapeHtml(points.at(-1).date)}</text></svg>`;
  }

  function applyLanguage() {
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en"; document.title = t("title"); $("h1").textContent = t("title"); $("#language-toggle").textContent = language === "zh" ? "EN" : "中文";
    $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); }); renderMeta(); renderSummary(); renderDimensions(); renderIndicators(); renderCombinations(); renderSelectAndPending(); renderTrend();
  }

  $("#language-toggle").addEventListener("click", () => { language = language === "zh" ? "en" : "zh"; localStorage.setItem("macro-language", language); applyLanguage(); });
  initTabs(); initTrendControls(); applyLanguage();
})();
