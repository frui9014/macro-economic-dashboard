(function () {
  "use strict";

  const data = window.MACRO_DASHBOARD_DATA;
  if (!data) {
    document.body.innerHTML = "<p style='padding:2rem;font-family:sans-serif'>Data file missing / 数据文件缺失</p>";
    return;
  }

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  let frequencyFilter = "all";
  let activePreset = null;
  let rangeState = null;
  let language = localStorage.getItem("macro-language") === "en" ? "en" : "zh";

  const UI = {
    zh: {
      title: "宏观经济观察", tabToday: "当日数据", tabTrends: "时间变化", tabAnalysis: "分析判断", todayView: "今日总判断",
      dimensions: "八维状态", dimensionsHint: "市场信号与宏观事实分层展示", thermometer: "今日温度计",
      thermometerHint: "点击指标查看可能原因与后果", combinations: "组合观察", combinationsHint: "共振比单一指标更重要",
      learningNote: "宏观学习笔记", indicator: "指标", frequencyFilter: "更新频次", frequencyAll: "全部", frequencyDaily: "每日", frequencyMonthly: "月度", frequencyQuarterly: "季度", frequencyAnnual: "年度", startPeriod: "起始时间", endPeriod: "终止时间",
      pending: "待接入数据", pendingHint: "缺失不会被伪造或静默填充", schedule: "每日 18:30（北京时间）更新",
      updated: "更新于", beijing: "北京时间", source: "来源", frequency: "日频", daily: "日", day5: "5日", day20: "20日", previous: "前值", forecast: "预期", fresh: "最新", staleData: "陈旧", unknownFreshness: "日期未知",
      reason: "可能原因", consequence: "可能后果", stale: "保留上次有效值", latestMove: "最新日变动", periodMove: "较前值", intervalMove: "区间变化",
      intervalRange: "区间范围", insufficient: "历史观测不足。", noErrors: (n) => `共更新 ${n} 项日频序列；低频指标只在发布日进入当日页。`,
      errors: (n) => `${n} 个数据源本次扫描未取得新值；已有数据保持不变。`, notice: "用于宏观学习与公共政策研究，不构成投资建议。",
      analysisEyebrow: "规则化宏观诊断", analysisDisclaimer: "本页面基于公开宏观数据、固定规则打分和 GPT 辅助解读生成。本系统用于宏观学习和研究观察，不构成投资建议。",
      scoreCards: "8 个维度打分", scoreHint: "+1 顺风 · 0 中性 · -1 逆风", relationTitle: "7 个组合关系", relationHint: "跨维度共振与传导诊断",
      relationName: "关系", conclusion: "结论", evidence: "证据", risk: "风险提示", confidence: "置信度", divergenceTitle: "今日背离信号", divergenceHint: "优先展示最值得复核的三条",
      mainAnalysis: "主体分析", watchlist: "后续观察指标", dataQuality: "数据质量", analysisLearning: "今日宏观学习笔记", positiveDriver: "正向", negativeDriver: "拖累", none: "暂无", currentData: "有效", staleCount: "陈旧", missingCount: "缺失", ruleMode: "未启用 GPT 解读，仅展示规则引擎分析结果", gptMode: "规则分析 + GPT 解读", noDivergence: "暂未检测到达到阈值的重要背离。", insufficientEvidence: "证据不足，不进入主判断", staleBackground: "数据较旧，仅作背景", missingExcluded: "数据缺失，未参与打分", totalSignal: "总量", structureSignal: "结构", effectiveCredit: "有效扩张", salesSide: "销售端", developmentSide: "开发端", priceSide: "价格端", evidenceQuality: "证据质量", yes: "是", no: "否"
    },
    en: {
      title: "Macro Observatory", tabToday: "Today", tabTrends: "Trends", tabAnalysis: "Analysis", todayView: "Today’s Macro View",
      dimensions: "Eight Dimensions", dimensionsHint: "Market signals separated from macro facts", thermometer: "Daily Indicators",
      thermometerHint: "Open a card for possible drivers and implications", combinations: "Combined Signals", combinationsHint: "Co-movement matters more than one series",
      learningNote: "Macro Learning Note", indicator: "Indicator", frequencyFilter: "Frequency", frequencyAll: "All", frequencyDaily: "Daily", frequencyMonthly: "Monthly", frequencyQuarterly: "Quarterly", frequencyAnnual: "Annual", startPeriod: "Start", endPeriod: "End",
      pending: "Pending Data", pendingHint: "Missing observations are never fabricated or silently filled", schedule: "Updated daily at 18:30 Beijing time",
      updated: "Updated", beijing: "Beijing time", source: "Source", frequency: "Daily", daily: "1D", day5: "5D", day20: "20D", previous: "Previous", forecast: "Forecast", fresh: "Current", staleData: "Stale", unknownFreshness: "Date unknown",
      reason: "Possible driver", consequence: "Possible implication", stale: "Last valid value retained", latestMove: "Latest daily move", periodMove: "Vs. previous", intervalMove: "Period change",
      intervalRange: "Range", insufficient: "Insufficient history.", noErrors: (n) => `${n} daily series updated; lower-frequency data appear only on release days.`,
      errors: (n) => `${n} source(s) failed in this run; last valid values were retained.`, notice: "For macro learning and public-policy research; not investment advice.",
      analysisEyebrow: "RULE-BASED MACRO DIAGNOSIS", analysisDisclaimer: "Built from public macro data, fixed scoring rules, and optional GPT interpretation. For research and learning only; not investment advice.",
      scoreCards: "Eight Dimension Scores", scoreHint: "+1 tailwind · 0 neutral · -1 headwind", relationTitle: "Seven Combined Diagnostics", relationHint: "Cross-dimension co-movement and transmission",
      relationName: "Relation", conclusion: "Conclusion", evidence: "Evidence", risk: "Risk note", confidence: "Confidence", divergenceTitle: "Key Divergences", divergenceHint: "The three signals most worth reviewing",
      mainAnalysis: "Main Analysis", watchlist: "Next Watchlist", dataQuality: "Data Quality", analysisLearning: "Macro Learning Note", positiveDriver: "Support", negativeDriver: "Drag", none: "None", currentData: "current", staleCount: "stale", missingCount: "missing", ruleMode: "Rules only · GPT off", gptMode: "Rules + GPT interpretation", noDivergence: "No divergence has crossed the configured threshold.", insufficientEvidence: "Insufficient evidence · excluded from the main view", staleBackground: "Older data · background only", missingExcluded: "Missing · excluded from scoring", totalSignal: "Total", structureSignal: "Structure", effectiveCredit: "Effective", salesSide: "Sales", developmentSide: "Development", priceSide: "Prices", evidenceQuality: "Evidence", yes: "Yes", no: "No"
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
  const ANALYSIS_DIMENSION_NAMES = { external_financial_pressure: "External Financial Pressure", global_demand: "Global Demand / External Demand", china_production: "China Production / Activity", china_domestic_demand: "China Domestic Demand", credit_expansion: "Credit Expansion", real_estate_cycle: "Real Estate Cycle", price_pressure: "Price / Deflation Pressure", innovation_upgrade: "Innovation & Upgrading" };
  const RELATION_NAMES = { production_vs_domestic_demand: "Production vs Domestic Demand", credit_vs_domestic_demand: "Credit vs Domestic Demand", credit_vs_real_estate: "Credit vs Real Estate", growth_vs_price: "Growth vs Prices", global_demand_vs_china_exports: "Global Demand vs China Exports", external_financial_pressure_vs_china_assets: "External Pressure vs China Assets", innovation_vs_hightech_exports: "Innovation vs High-tech Exports" };
  const STATE_NAMES = { "真复苏": "Broad-based Recovery", "供给强、需求弱": "Strong Supply, Weak Demand", "政策托底型增长": "Policy-supported Growth", "信用传导不畅": "Weak Credit Transmission", "地产拖累": "Real Estate Drag", "通缩压力": "Deflation Pressure", "外部逆风": "External Headwinds", "外需顺风": "External-demand Tailwind", "创新升级增强": "Stronger Innovation Upgrading", "数据分化、暂难判断": "Mixed Data, No Clear Regime" };
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
    const activate = (name) => { $$(".tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === name)); $$(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === name)); if (name === "trends") renderTrend(); if (name === "analysis") renderAnalysis(); };
    $$(".tab").forEach((button) => button.addEventListener("click", () => { window.location.hash = button.dataset.tab; activate(button.dataset.tab); }));
    const requested = window.location.hash.replace("#", ""); if (["today", "trends", "analysis"].includes(requested)) activate(requested);
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
    $("#dimensions").innerHTML = data.dimensions.map((item) => `<article class="dimension"><span class="dimension-name">${escapeHtml(dimensionName(item.name))}</span><strong class="dimension-status">${escapeHtml(term(item.status))}</strong><span class="dimension-meta">${escapeHtml(term(item.freshness))}</span></article>`).join("");
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

  function analysisName(item) { return language === "en" ? (ANALYSIS_DIMENSION_NAMES[item.dimension_id] || item.dimension_name) : item.dimension_name; }
  function relationName(item) { return language === "en" ? (RELATION_NAMES[item.relation_id] || item.relation_name) : item.relation_name; }
  function confidenceText(value) { return language === "en" ? ({ "高": "High", "中": "Medium", "低": "Low" }[value] || value) : value; }
  function stateName(value) { return language === "en" ? (STATE_NAMES[value] || value) : value; }
  function scoreClass(value) { return value >= .5 ? "positive-score" : value <= -.5 ? "negative-score" : "neutral-score"; }
  function listText(items) { return items?.length ? items.join(language === "en" ? ", " : "、") : t("none"); }

  function dimensionDiagnostics(item) {
    if (item.dimension_id === "credit_expansion") return `<div class="dimension-diagnostics"><span>${t("totalSignal")} <b>${escapeHtml(item.total_judgement || "—")}</b></span><span>${t("structureSignal")} <b>${escapeHtml(item.structure_judgement || "—")}</b></span><span>${t("effectiveCredit")} <b>${item.effective_expansion ? t("yes") : t("no")}</b></span></div>`;
    if (item.dimension_id === "real_estate_cycle") return `<div class="dimension-diagnostics four"><span>${t("salesSide")} <b>${escapeHtml(item.sales_side || "—")}</b></span><span>${t("developmentSide")} <b>${escapeHtml(item.development_side || "—")}</b></span><span>${t("priceSide")} <b>${escapeHtml(item.price_side || "—")}</b></span><span>${t("evidenceQuality")} <b>${escapeHtml(item.evidence_quality || "—")}</b></span></div>`;
    return "";
  }

  function renderAnalysis() {
    const analysis = data.analysis; const judgement = data.macro_judgement;
    if (!analysis || !judgement) { $("#analysis-summary").textContent = language === "zh" ? "分析数据尚未生成。" : "Analysis data have not been generated yet."; return; }
    $("#analysis-summary").textContent = judgement.one_sentence_summary || analysis.rule_summary;
    $("#macro-states").innerHTML = (judgement.macro_state_labels?.length ? judgement.macro_state_labels : analysis.candidate_macro_states).map((item) => `<span class="state-tag">${escapeHtml(stateName(item))}</span>`).join("");
    $("#analysis-mode").textContent = judgement.gpt_enabled ? t("gptMode") : t("ruleMode");
    $("#analysis-dimensions").innerHTML = analysis.dimension_scores.map((item) => {
      const confidenceClass = item.confidence === "低" ? "confidence-low" : ""; const score = item.score == null ? "—" : `${item.score > 0 ? "+" : ""}${Number(item.score).toFixed(2)}`;
      const weak = item.evidence_quality === "weak" || !item.can_be_macro_state;
      const dataNotes = `${(item.stale_indicators || []).length ? `<span title="${escapeHtml(listText(item.stale_indicators))}">${t("staleBackground")}</span>` : ""}${(item.missing_indicators || []).length ? `<span title="${escapeHtml(listText(item.missing_indicators))}">${t("missingExcluded")}</span>` : ""}`;
      return `<article class="score-card ${scoreClass(item.score)} ${weak ? "evidence-insufficient" : ""}"><div class="score-head"><span class="score-name">${escapeHtml(analysisName(item))}</span><strong class="score-number">${score}</strong></div><strong class="score-label">${escapeHtml(item.label)}</strong>${weak ? `<p class="evidence-notice">${t("insufficientEvidence")}</p>` : ""}<div class="score-meta"><span class="confidence-chip ${confidenceClass}">${t("confidence")} ${escapeHtml(confidenceText(item.confidence))}</span><span>${Math.round((item.coverage || 0) * 100)}% coverage</span></div>${dimensionDiagnostics(item)}<div class="driver-block"><p class="driver-line"><b>${t("positiveDriver")}：</b>${escapeHtml(listText(item.top_positive_drivers))}</p><p class="driver-line"><b>${t("negativeDriver")}：</b>${escapeHtml(listText(item.top_negative_drivers))}</p></div><p class="freshness-line">${t("currentData")} ${(item.updated_indicators || []).length} · ${t("staleCount")} ${(item.stale_indicators || []).length} · ${t("missingCount")} ${(item.missing_indicators || []).length}</p>${dataNotes ? `<p class="data-evidence-notes">${dataNotes}</p>` : ""}</article>`;
    }).join("");
    $("#analysis-relations").innerHTML = analysis.relation_diagnostics.map((item) => `<tr class="${item.evidence_quality === "weak" ? "evidence-row-weak" : ""}"><td>${escapeHtml(relationName(item))}</td><td>${escapeHtml(item.conclusion)}${item.can_enter_summary ? "" : `<span class="table-evidence-note">${t("insufficientEvidence")}</span>`}</td><td>${escapeHtml(listText(item.evidence))}</td><td>${escapeHtml(item.risk_note)}</td><td>${escapeHtml(confidenceText(item.confidence))}</td></tr>`).join("");
    const divergences = analysis.detected_divergences.slice(0, 3);
    $("#analysis-divergences").innerHTML = divergences.length ? divergences.map((item) => `<article class="divergence-card"><div class="divergence-head"><h4>${escapeHtml(item.title)}</h4><span class="severity ${item.severity === "高" ? "high" : ""}">${escapeHtml(item.severity)}</span></div><p>${escapeHtml(item.interpretation)}</p><div class="divergence-watch">${t("watchlist")} · ${escapeHtml(listText(item.what_to_watch_next))}</div></article>`).join("") : `<div class="empty-analysis">${t("noDivergence")}</div>`;
    $("#analysis-main").textContent = judgement.main_judgement || analysis.rule_summary;
    const interpretations = judgement.dimension_interpretations || [];
    $("#analysis-interpretations").innerHTML = interpretations.slice(0, 4).map((item) => `<div class="analysis-interpretation"><strong>${escapeHtml(language === "en" ? (ANALYSIS_DIMENSION_NAMES[item.dimension_id] || item.dimension_name) : item.dimension_name)}</strong><p>${escapeHtml(item.interpretation)}</p></div>`).join("");
    const watchlist = judgement.next_watchlist || [];
    $("#analysis-watchlist").innerHTML = (watchlist.length ? watchlist : [language === "zh" ? "等待下一批关键数据更新" : "Wait for the next key data releases"]).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const freshness = analysis.data_freshness;
    $("#analysis-quality").innerHTML = `<div class="quality-row"><span>${t("currentData")}</span><strong>${freshness.new_updates_today.length + freshness.recent_indicators.length}</strong></div><div class="quality-row"><span>${t("staleCount")}</span><strong>${freshness.stale_indicators.length}</strong></div><div class="quality-row"><span>${t("missingCount")}</span><strong>${freshness.missing_indicators.length}</strong></div><div class="quality-row"><span>${t("confidence")}</span><strong>${escapeHtml(confidenceText(judgement.data_confidence))}</strong></div>`;
    $("#analysis-learning-note").textContent = judgement.learning_note || (language === "zh" ? "先观察信号是否跨频率共振，再判断单项变化是否代表趋势。" : "Look for cross-frequency confirmation before treating one move as a trend.");
  }

  const PENDING_EN = { "中国 10 年期国债": ["China 10Y Government Bond", "Stable, compliant public interface under review"], "中国内部月度宏观": ["China Monthly Macro", "Official releases planned for phase two"], "创新升级指标": ["Innovation & Upgrading", "Monthly and annual series planned for phase four"] };
  const RANGE_PRESETS = {
    daily: [{ id: "7d", span: 7, zh: "7日", en: "7D" }, { id: "1m", span: 30, zh: "1月", en: "1M" }, { id: "3m", span: 90, zh: "3月", en: "3M", default: true }, { id: "1y", span: 365, zh: "1年", en: "1Y" }],
    monthly: [{ id: "1y", span: 12, zh: "1年", en: "1Y" }, { id: "3y", span: 36, zh: "3年", en: "3Y" }, { id: "5y", span: 60, zh: "5年", en: "5Y", default: true }, { id: "10y", span: 120, zh: "10年", en: "10Y" }],
    quarterly: [{ id: "3y", span: 12, zh: "3年", en: "3Y" }, { id: "5y", span: 20, zh: "5年", en: "5Y" }, { id: "10y", span: 40, zh: "10年", en: "10Y", default: true }, { id: "20y", span: 80, zh: "20年", en: "20Y" }],
    annual: [{ id: "5y", span: 5, zh: "5年", en: "5Y" }, { id: "10y", span: 10, zh: "10年", en: "10Y" }, { id: "15y", span: 15, zh: "15年", en: "15Y", default: true }, { id: "all", span: null, zh: "全部", en: "All" }]
  };

  function trendFrequency(item) { return ["daily", "monthly", "quarterly", "annual"].includes(item.frequency) ? item.frequency : "daily"; }
  function periodKey(value, frequency) {
    const text = String(value ?? ""); const nums = (text.match(/\d+/g) || []).map(Number); if (!nums.length) return null;
    let year = nums[0], month = nums[1] || 1, day = nums[2] || 1;
    if (year >= 100000) { month = year % 100; year = Math.floor(year / 100); }
    if (frequency === "annual") return year;
    if (frequency === "quarterly") { const quarter = /q|季度|季/i.test(text) && nums[1] ? nums[1] : Math.ceil(month / 3); return year * 4 + Math.max(0, Math.min(3, quarter - 1)); }
    if (frequency === "monthly") return year * 12 + Math.max(0, Math.min(11, month - 1));
    return Math.floor(Date.UTC(year, Math.max(0, month - 1), Math.max(1, day)) / 86400000);
  }
  function currentPeriodKey(frequency) {
    const now = new Date();
    if (frequency === "annual") return now.getFullYear();
    if (frequency === "quarterly") return now.getFullYear() * 4 + Math.floor(now.getMonth() / 3);
    if (frequency === "monthly") return now.getFullYear() * 12 + now.getMonth();
    return Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000);
  }
  function periodLabel(key, frequency) {
    if (frequency === "annual") return String(key);
    if (frequency === "quarterly") return `${Math.floor(key / 4)}-Q${key % 4 + 1}`;
    if (frequency === "monthly") { const year = Math.floor(key / 12), month = key % 12 + 1; return `${year}-${String(month).padStart(2, "0")}`; }
    return new Date(key * 86400000).toISOString().slice(0, 10);
  }
  function axisLabel(key, frequency) {
    const label = periodLabel(key, frequency);
    if (frequency === "daily" && rangeState && rangeState.end - rangeState.start <= 120) return label.slice(5);
    return label;
  }
  function historyBounds(item) {
    const frequency = trendFrequency(item); const keys = item.history.map((point) => periodKey(point.date, frequency)).filter(Number.isFinite);
    return { min: Math.min(...keys), max: Math.max(...keys) };
  }
  function setDefaultRange(item) {
    const frequency = trendFrequency(item), presets = RANGE_PRESETS[frequency], preset = presets.find((entry) => entry.default) || presets[0], end = currentPeriodKey(frequency), bounds = historyBounds(item);
    activePreset = preset.id;
    rangeState = { frequency, start: preset.span == null ? bounds.min : end - preset.span + 1, end };
  }
  function renderRangeSwitch(item) {
    const frequency = trendFrequency(item), container = $("#range-switch");
    container.innerHTML = RANGE_PRESETS[frequency].map((preset) => `<button type="button" data-preset="${preset.id}" class="${activePreset === preset.id ? "active" : ""}">${preset[language]}</button>`).join("");
    container.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
      const preset = RANGE_PRESETS[frequency].find((entry) => entry.id === button.dataset.preset), end = currentPeriodKey(frequency), bounds = historyBounds(item);
      activePreset = preset.id; rangeState = { frequency, start: preset.span == null ? bounds.min : end - preset.span + 1, end }; renderTrend();
    }));
  }
  function periodControl(target, item, boundary) {
    const frequency = trendFrequency(item), value = rangeState[boundary], bounds = historyBounds(item); let control;
    if (frequency === "daily" || frequency === "monthly") {
      control = document.createElement("input"); control.type = frequency === "daily" ? "date" : "month"; control.value = periodLabel(value, frequency);
    } else {
      control = document.createElement("select"); const first = Math.min(bounds.min, rangeState.start), last = Math.max(currentPeriodKey(frequency), bounds.max, rangeState.end);
      for (let key = last; key >= first; key -= 1) { const option = document.createElement("option"); option.value = periodLabel(key, frequency); option.textContent = periodLabel(key, frequency); control.appendChild(option); }
      control.value = periodLabel(value, frequency);
    }
    control.className = "period-control"; control.setAttribute("aria-label", boundary === "start" ? t("startPeriod") : t("endPeriod"));
    control.addEventListener("change", () => {
      const next = periodKey(control.value, frequency); if (!Number.isFinite(next)) return;
      rangeState[boundary] = next;
      if (rangeState.start > rangeState.end) rangeState[boundary === "start" ? "end" : "start"] = next;
      activePreset = null; renderTrend();
    });
    const host = $(target); host.innerHTML = ""; host.appendChild(control);
  }
  function renderDateControls(item) { periodControl("#start-control", item, "start"); periodControl("#end-control", item, "end"); }

  function renderSelectAndPending(resetSelection = false) {
    const select = $("#indicator-select"); const chosen = select.value;
    const candidates = [...data.indicators].filter((item) => item.history?.length && (frequencyFilter === "all" || trendFrequency(item) === frequencyFilter)).sort((a, b) => priorityRank(a) - priorityRank(b));
    select.innerHTML = candidates.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(displayName(item))}</option>`).join("");
    if (!resetSelection && [...select.options].some((option) => option.value === chosen)) select.value = chosen;
    else if (select.options.length) select.selectedIndex = 0;
    $("#pending").innerHTML = data.pending.map((item) => { const en = PENDING_EN[item.name]; const name = language === "en" ? (item.name_en || en?.[0] || item.name) : item.name; const reason = language === "en" ? (item.reason_en || en?.[1] || item.reason) : item.reason; return `<div class="pending-item"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(reason)}</span></div>`; }).join("");
    if (resetSelection) rangeState = null;
  }

  function initTrendControls() {
    $("#frequency-filter").addEventListener("change", (event) => { frequencyFilter = event.target.value; renderSelectAndPending(true); renderTrend(); });
    $("#indicator-select").addEventListener("change", () => { rangeState = null; renderTrend(); });
  }

  function renderTrend() {
    const item = data.indicators.find((indicator) => indicator.id === $("#indicator-select").value); if (!item) return;
    const frequency = trendFrequency(item); if (!rangeState || rangeState.frequency !== frequency) setDefaultRange(item); renderRangeSwitch(item); renderDateControls(item);
    const points = item.history.map((point) => ({ ...point, periodKey: periodKey(point.date, frequency) })).filter((point) => Number.isFinite(point.periodKey) && point.periodKey >= rangeState.start && point.periodKey <= rangeState.end).sort((a, b) => a.periodKey - b.periodKey);
    $("#trend-name").textContent = displayName(item); $("#trend-value").innerHTML = `${formatValue(item)} <span class="unit">${escapeHtml(displayUnit(item))}</span>`;
    const latestMove = frequency === "daily" ? item.day_change : (item.previous_value == null ? null : pct(item.value, item.previous_value));
    $("#trend-change").className = `trend-change ${moveClass(latestMove)}`; $("#trend-change").textContent = `${frequency === "daily" ? t("latestMove") : t("periodMove")} ${formatMove(latestMove, frequency === "daily" ? item.change_unit : "%")}`; drawChart(points, item.decimals, frequency);
    if (!points.length) { $("#trend-details").innerHTML = `<p class="muted">${t("insufficient")}</p>`; return; }
    const values = points.map((point) => point.value); const low = Math.min(...values); const high = Math.max(...values); const intervalMove = pct(values.at(-1), values[0]);
    $("#trend-details").innerHTML = `<div class="trend-detail"><span>${t("intervalMove")}</span><strong class="${moveClass(intervalMove)}">${formatMove(intervalMove, "%")}</strong></div><div class="trend-detail"><span>${t("intervalRange")}</span><strong>${low.toFixed(item.decimals)} — ${high.toFixed(item.decimals)}</strong></div><div class="trend-detail"><span>${t("source")} · ${frequencyLabel(item)}</span><strong>${escapeHtml(displaySource(item))}</strong></div>`;
  }

  function pct(current, previous) { return previous ? (current / previous - 1) * 100 : null; }
  function drawChart(points, decimals, frequency) {
    const chart = $("#chart"); if (points.length < 2) { chart.innerHTML = `<p class="muted">${t("insufficient")}</p>`; return; }
    const width = 1000, height = 330, pad = { top: 20, right: 20, bottom: 30, left: 55 }; const values = points.map((point) => point.value); let min = Math.min(...values), max = Math.max(...values); const spread = max - min || Math.abs(max) * .02 || 1; min -= spread * .12; max += spread * .12;
    const domainStart = rangeState.start, domainEnd = Math.max(rangeState.end, domainStart + 1); const x = (key) => pad.left + (key - domainStart) * (width - pad.left - pad.right) / (domainEnd - domainStart); const y = (value) => pad.top + (max - value) * (height - pad.top - pad.bottom) / (max - min);
    const line = points.map((point, index) => `${index ? "L" : "M"}${x(point.periodKey).toFixed(1)},${y(point.value).toFixed(1)}`).join(" "); const area = `${line} L${x(points.at(-1).periodKey)},${height - pad.bottom} L${x(points[0].periodKey)},${height - pad.bottom} Z`;
    const ticks = [0, .25, .5, .75, 1].map((ratio) => { const value = min + (max - min) * ratio, yy = y(value); return `<line class="chart-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${yy}" y2="${yy}"/><text class="chart-label" x="${pad.left - 8}" y="${yy + 3}" text-anchor="end">${value.toFixed(decimals)}</text>`; }).join("");
    const xTickKeys = [...new Set([0, .25, .5, .75, 1].map((ratio) => Math.round(domainStart + (domainEnd - domainStart) * ratio)))];
    const xTicks = xTickKeys.map((key, index) => `<line class="chart-grid x-grid" x1="${x(key)}" x2="${x(key)}" y1="${pad.top}" y2="${height - pad.bottom}"/><text class="chart-label" x="${x(key)}" y="${height - 8}" text-anchor="${index === 0 ? "start" : index === xTickKeys.length - 1 ? "end" : "middle"}">${escapeHtml(axisLabel(key, frequency))}</text>`).join("");
    chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#175c45" stop-opacity=".16"/><stop offset="1" stop-color="#175c45" stop-opacity="0"/></linearGradient></defs>${ticks}${xTicks}<path class="chart-area" d="${area}"/><path class="chart-line" d="${line}"/></svg>`;
  }

  function applyLanguage() {
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en"; document.title = t("title"); $("h1").textContent = t("title"); $("#language-toggle").textContent = language === "zh" ? "EN" : "中文";
    $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); }); renderMeta(); renderSummary(); renderDimensions(); renderIndicators(); renderCombinations(); renderSelectAndPending(); renderTrend(); renderAnalysis();
  }

  $("#language-toggle").addEventListener("click", () => { language = language === "zh" ? "en" : "zh"; localStorage.setItem("macro-language", language); applyLanguage(); });
  initTabs(); initTrendControls(); applyLanguage();
})();
