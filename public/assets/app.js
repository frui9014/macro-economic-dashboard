(function () {
  "use strict";

  const data = window.MACRO_DASHBOARD_DATA;
  if (!data) {
    document.body.innerHTML = "<p style='padding:2rem;font-family:sans-serif'>数据文件缺失，请先运行更新程序。</p>";
    return;
  }

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  let rangeDays = 30;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatValue(item) {
    return Number(item.value).toLocaleString("zh-CN", {
      minimumFractionDigits: item.decimals,
      maximumFractionDigits: item.decimals,
    });
  }

  function formatMove(value, unit) {
    if (value === null || value === undefined || Number.isNaN(value)) return "—";
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${Number(value).toFixed(unit === "bp" ? 1 : 2)}${unit}`;
  }

  function moveClass(value) {
    return value > 0 ? "positive" : value < 0 ? "negative" : "";
  }

  function initTabs() {
    const activate = (name) => {
      $$(".tab").forEach((item) => item.classList.toggle("active", item.dataset.tab === name));
      $$(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === name));
      if (name === "trends") renderTrend();
    };
    $$(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        window.location.hash = button.dataset.tab;
        activate(button.dataset.tab);
      });
    });
    if (window.location.hash === "#trends") activate("trends");
  }

  function renderMeta() {
    $("#update-time").textContent = `更新于 ${data.meta.generated_label} · 北京时间`;
    $("#health-dot").classList.add(data.meta.status);
    $("#data-notice").textContent = data.meta.error_count
      ? `${data.meta.error_count} 个数据源本次更新失败，页面已保留可用旧值。`
      : `共更新 ${data.meta.indicator_count} 项日频序列；低频指标只在发布日进入当日页。`;
    $("#footer-notice").textContent = data.meta.notice;
  }

  function renderSummary() {
    const map = Object.fromEntries(data.dimensions.map((item) => [item.name, item.status]));
    $("#daily-summary").textContent = `全球流动性${map["全球流动性"]}，全球需求${map["全球需求"]}；中国资产${map["中国增长"]}，通胀${map["通胀压力"]}。`;
  }

  function renderDimensions() {
    $("#dimensions").innerHTML = data.dimensions.map((item) => `
      <article class="dimension">
        <span class="dimension-name">${escapeHtml(item.name)}</span>
        <strong class="dimension-status">${escapeHtml(item.status)}</strong>
        <span class="dimension-meta">置信度 ${escapeHtml(item.confidence)} · ${escapeHtml(item.freshness)}</span>
      </article>
    `).join("");
  }

  function renderIndicators() {
    const groups = {};
    data.indicators.forEach((item) => {
      (groups[item.group] ||= []).push(item);
    });
    $("#indicator-groups").innerHTML = Object.entries(groups).map(([name, items]) => `
      <div class="group-block">
        <h4 class="group-title">${escapeHtml(name)}</h4>
        <div class="indicator-grid">
          ${items.map((item) => `
            <details class="indicator">
              <summary>
                <div class="indicator-top">
                  <span class="indicator-name">${escapeHtml(item.name)}</span>
                  <span class="indicator-date">${escapeHtml(item.date)}</span>
                </div>
                <div class="indicator-value">${formatValue(item)}<span class="unit">${escapeHtml(item.unit)}</span></div>
                <div class="moves">
                  <span>日 <b class="${moveClass(item.day_change)}">${formatMove(item.day_change, item.change_unit)}</b></span>
                  <span>5日 <b class="${moveClass(item.five_change)}">${formatMove(item.five_change, item.change_unit)}</b></span>
                  <span>20日 <b class="${moveClass(item.twenty_change)}">${formatMove(item.twenty_change, item.change_unit)}</b></span>
                </div>
                ${item.status === "stale" ? '<span class="stale-badge">保留上次有效值</span>' : ""}
              </summary>
              <div class="indicator-detail">
                <p><strong>可能原因：</strong>${escapeHtml(item.reason)}</p>
                <p><strong>可能后果：</strong>${escapeHtml(item.consequence)}</p>
                <p><a class="source-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.source)}</a></p>
              </div>
            </details>
          `).join("")}
        </div>
      </div>
    `).join("");
  }

  function renderCombinations() {
    $("#combinations").innerHTML = data.combinations.map((item) => `
      <article class="combination">
        <div class="combination-head">
          <h4>${escapeHtml(item.title)}</h4>
          <span class="signal">${escapeHtml(item.signal)}</span>
        </div>
        <p>${escapeHtml(item.analysis)}</p>
      </article>
    `).join("");
    $("#learning-note").textContent = data.learning_note;
  }

  function initTrendControls() {
    const select = $("#indicator-select");
    select.innerHTML = data.indicators
      .filter((item) => item.history && item.history.length)
      .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`)
      .join("");
    select.addEventListener("change", renderTrend);
    $$(".range-switch button").forEach((button) => {
      button.addEventListener("click", () => {
        $$(".range-switch button").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        rangeDays = Number(button.dataset.days);
        renderTrend();
      });
    });
    $("#pending").innerHTML = data.pending.map((item) => `
      <div class="pending-item"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.reason)}</span></div>
    `).join("");
  }

  function renderTrend() {
    const selectedId = $("#indicator-select").value;
    const item = data.indicators.find((indicator) => indicator.id === selectedId);
    if (!item) return;
    const points = item.history.slice(-rangeDays);
    $("#trend-name").textContent = item.name;
    $("#trend-value").innerHTML = `${formatValue(item)} <span class="unit">${escapeHtml(item.unit)}</span>`;
    $("#trend-change").className = `trend-change ${moveClass(item.day_change)}`;
    $("#trend-change").textContent = `最新日变动 ${formatMove(item.day_change, item.change_unit)}`;
    drawChart(points, item.decimals);
    const values = points.map((point) => point.value);
    const low = Math.min(...values);
    const high = Math.max(...values);
    const intervalMove = pct(values[values.length - 1], values[0]);
    $("#trend-details").innerHTML = `
      <div class="trend-detail"><span>区间变化</span><strong class="${moveClass(intervalMove)}">${formatMove(intervalMove, "%")}</strong></div>
      <div class="trend-detail"><span>区间范围</span><strong>${low.toFixed(item.decimals)} — ${high.toFixed(item.decimals)}</strong></div>
      <div class="trend-detail"><span>数据来源</span><strong>${escapeHtml(item.source)}</strong></div>
    `;
  }

  function pct(current, previous) {
    if (!previous) return null;
    return (current / previous - 1) * 100;
  }

  function drawChart(points, decimals) {
    const chart = $("#chart");
    if (points.length < 2) {
      chart.innerHTML = "<p class='muted'>历史观测不足。</p>";
      return;
    }
    const width = 1000;
    const height = 330;
    const pad = { top: 20, right: 20, bottom: 30, left: 55 };
    const values = points.map((point) => point.value);
    let min = Math.min(...values);
    let max = Math.max(...values);
    const spread = max - min || Math.abs(max) * .02 || 1;
    min -= spread * .12;
    max += spread * .12;
    const x = (index) => pad.left + index * (width - pad.left - pad.right) / (points.length - 1);
    const y = (value) => pad.top + (max - value) * (height - pad.top - pad.bottom) / (max - min);
    const line = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`).join(" ");
    const area = `${line} L${x(points.length - 1)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z`;
    const ticks = [0, .25, .5, .75, 1].map((ratio) => {
      const value = min + (max - min) * ratio;
      const yy = y(value);
      return `<line class="chart-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${yy}" y2="${yy}"/><text class="chart-label" x="${pad.left - 8}" y="${yy + 3}" text-anchor="end">${value.toFixed(decimals)}</text>`;
    }).join("");
    const firstDate = points[0].date;
    const lastDate = points[points.length - 1].date;
    chart.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#175c45" stop-opacity=".16"/><stop offset="1" stop-color="#175c45" stop-opacity="0"/></linearGradient></defs>
        ${ticks}
        <path class="chart-area" d="${area}"/>
        <path class="chart-line" d="${line}"/>
        <text class="chart-label" x="${pad.left}" y="${height - 8}">${escapeHtml(firstDate)}</text>
        <text class="chart-label" x="${width - pad.right}" y="${height - 8}" text-anchor="end">${escapeHtml(lastDate)}</text>
      </svg>`;
  }

  initTabs();
  renderMeta();
  renderSummary();
  renderDimensions();
  renderIndicators();
  renderCombinations();
  initTrendControls();
  renderTrend();
})();
