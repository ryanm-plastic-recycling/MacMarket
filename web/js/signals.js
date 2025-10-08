const state = {
  symbol: null,
  mode: null,
  payload: null,
  chart: null,
};

const API_BASE = "/api";

function $(selector) {
  return document.querySelector(selector);
}

function getParams() {
  const url = new URL(window.location.href);
  const symbol = (url.searchParams.get("symbol") || "SPY").toUpperCase();
  const mode = (url.searchParams.get("mode") || "swing").toLowerCase();
  return { symbol, mode };
}

function updateQuery(symbol, mode) {
  const url = new URL(window.location.href);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("mode", mode);
  window.history.replaceState({}, "", url);
}

async function fetchSignals(symbol, mode) {
  const response = await fetch(`${API_BASE}/signals/${symbol}?mode=${mode}`);
  if (!response.ok) {
    throw new Error("Unable to load signal data");
  }
  return response.json();
}

function renderModeSwitcher(modes) {
  const container = document.getElementById("mode-switcher");
  container.innerHTML = "";
  modes.forEach((mode) => {
    const btn = document.createElement("button");
    btn.textContent = mode.name;
    btn.dataset.mode = mode.id;
    if (mode.id === state.mode) btn.classList.add("active");
    btn.title = `Primary timeframes: ${mode.timeframes.join(", ")}`;
    btn.addEventListener("click", () => {
      if (state.mode === mode.id) return;
      loadSignals(state.symbol, mode.id);
    });
    container.appendChild(btn);
  });
}

function renderWatchlist(symbols) {
  const container = document.getElementById("watchlist");
  container.innerHTML = "";
  symbols.forEach((sym) => {
    const btn = document.createElement("button");
    btn.textContent = sym;
    if (sym === state.symbol) btn.classList.add("active");
    btn.addEventListener("click", () => {
      if (state.symbol === sym) return;
      loadSignals(sym, state.mode);
    });
    container.appendChild(btn);
  });
}

function setMindsetText(mindset) {
  const container = document.getElementById("mode-mindset");
  container.textContent = mindset[state.mode] || "";
}

function polarStroke(percent) {
  const circumference = 2 * Math.PI * 54;
  return circumference - (percent / 100) * circumference;
}

function updateReadiness(readiness) {
  const ring = document.querySelector(".ring-progress");
  const label = document.getElementById("readiness-label");
  const value = document.getElementById("readiness-value");
  const detail = document.getElementById("readiness-detail");
  const percent = Math.round(readiness || 0);
  ring.style.strokeDashoffset = polarStroke(percent);
  value.textContent = `${percent}%`;
  if (percent >= 75) {
    label.textContent = "Ready";
    detail.textContent = "All core pillars aligned.";
  } else if (percent >= 50) {
    label.textContent = "Almost";
    detail.textContent = "Waiting for one more pillar to confirm.";
  } else {
    label.textContent = "Not Ready";
    detail.textContent = "Monitor HACO, RSI and ADX for alignment.";
  }
}

function renderPanels(panels) {
  const container = document.getElementById("panel-cards");
  container.innerHTML = "";
  panels.forEach((panel) => {
    const card = document.createElement("article");
    card.className = "panel-card";

    const status = document.createElement("div");
    status.className = `status ${panel.status === "PASS" ? "pass" : panel.status === "FAIL" ? "fail" : "info"}`;
    status.textContent = panel.status;

    const body = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = panel.title;
    title.className = "panel-title";

    const bar = document.createElement("div");
    bar.className = "bar";
    const span = document.createElement("span");
    span.style.width = `${Math.min(100, Math.max(0, panel.score))}%`;
    bar.appendChild(span);

    const reason = document.createElement("small");
    reason.textContent = panel.reason;

    body.appendChild(title);
    body.appendChild(bar);
    body.appendChild(reason);

    card.appendChild(status);
    card.appendChild(body);
    container.appendChild(card);
  });
}

function renderTabs(tabs) {
  const tabsContainer = document.getElementById("advanced-tabs");
  const body = document.getElementById("tab-body");
  tabsContainer.innerHTML = "";
  body.textContent = "";
  tabs.forEach((tab, index) => {
    const btn = document.createElement("button");
    btn.textContent = tab.title;
    btn.dataset.tab = tab.id;
    if (index === 0) {
      btn.classList.add("active");
      body.textContent = tab.description;
    }
    btn.addEventListener("click", () => {
      tabsContainer.querySelectorAll("button").forEach((el) => el.classList.remove("active"));
      btn.classList.add("active");
      body.textContent = tab.description + `\nFocus: ${tab.indicators.join(", ")}`;
    });
    tabsContainer.appendChild(btn);
  });
}

function renderSparkline(canvas, data, color = "#38bdf8") {
  const ctx = canvas.getContext("2d");
  const width = canvas.width = canvas.clientWidth || 220;
  const height = canvas.height = 80;
  ctx.clearRect(0, 0, width, height);
  if (!data || data.length === 0) return;
  const filtered = data.filter((v) => typeof v === "number" && !Number.isNaN(v));
  if (filtered.length === 0) return;
  const min = Math.min(...filtered);
  const max = Math.max(...filtered);
  const range = max - min || 1;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  data.forEach((value, i) => {
    const y = height - ((value - min) / range) * height;
    const x = (i / (data.length - 1 || 1)) * width;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderSubpanels(chartData) {
  const hacoCanvas = document.querySelector("#haco-panel canvas");
  const rsiCanvas = document.querySelector("#rsi-panel canvas");
  const adxCanvas = document.querySelector("#adx-panel canvas");
  renderSparkline(hacoCanvas, chartData.haco, "#38bdf8");
  renderSparkline(rsiCanvas, chartData.rsi, "#22c55e");
  renderSparkline(adxCanvas, chartData.adx, "#f97316");
}

function renderChart(chartData) {
  const element = document.getElementById("chart-area");
  element.innerHTML = "";
  state.chart = LightweightCharts.createChart(element, {
    layout: {
      background: { color: "rgba(15, 23, 42, 0.0)" },
      textColor: "#e2e8f0",
    },
    grid: {
      vertLines: { color: "rgba(148, 163, 184, 0.1)" },
      horzLines: { color: "rgba(148, 163, 184, 0.1)" },
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
    },
    timeScale: {
      borderVisible: false,
    },
    rightPriceScale: {
      borderVisible: false,
    },
  });

  const haSeries = state.chart.addCandlestickSeries({
    upColor: "#22c55e",
    downColor: "#ef4444",
    borderVisible: false,
    wickUpColor: "#22c55e",
    wickDownColor: "#ef4444",
  });

  const emaFast = state.chart.addLineSeries({ color: "#22d3ee", lineWidth: 2 });
  const emaSlow = state.chart.addLineSeries({ color: "#f97316", lineWidth: 2 });

  const candleData = chartData.ohlc.map((row) => ({
    time: row.time,
    open: row.ha_open,
    high: row.ha_high,
    low: row.ha_low,
    close: row.ha_close,
  }));
  haSeries.setData(candleData);

  const times = chartData.ohlc.map((row) => row.time);
  emaFast.setData(times.map((time, idx) => ({ time, value: chartData.ema_fast[idx] })));
  emaSlow.setData(times.map((time, idx) => ({ time, value: chartData.ema_slow[idx] })));

  renderSubpanels(chartData);
}

function setupAlertDrawer() {
  const drawer = document.getElementById("alert-drawer");
  const openBtn = document.getElementById("open-alert-drawer");
  const closeBtn = document.getElementById("close-alert-drawer");
  openBtn.addEventListener("click", () => {
    drawer.classList.add("active");
    drawer.setAttribute("aria-hidden", "false");
    document.getElementById("alert-symbol").value = state.symbol;
    document.getElementById("alert-mode").value = state.mode;
  });
  closeBtn.addEventListener("click", () => {
    drawer.classList.remove("active");
    drawer.setAttribute("aria-hidden", "true");
  });

  document.getElementById("alert-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      symbol: document.getElementById("alert-symbol").value.trim().toUpperCase(),
      mode: document.getElementById("alert-mode").value,
      tf: document.getElementById("alert-tf").value,
      channels: {
        email: document.getElementById("alert-email").value || undefined,
        sms: document.getElementById("alert-sms").value || undefined,
      },
      rules: {
        require_trend_pass: document.getElementById("rule-trend").checked,
        require_momentum_pass: document.getElementById("rule-momentum").checked,
        min_total_score: Number(document.getElementById("rule-score").value || 0),
      },
    };

    const preview = document.getElementById("alert-preview");
    preview.textContent = "Testing alert...";
    try {
      const response = await fetch(`${API_BASE}/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Alert preview failed");
      const result = await response.json();
      preview.textContent = `${result.message}\nTriggered: ${result.triggered ? "YES" : "Not yet"}`;
    } catch (error) {
      preview.textContent = `Error: ${error.message}`;
    }
  });
}

async function loadSignals(symbol, mode) {
  try {
    const payload = await fetchSignals(symbol, mode);
    state.symbol = payload.symbol;
    state.mode = payload.mode;
    state.payload = payload;
    updateQuery(state.symbol, state.mode);
    renderModeSwitcher(payload.available_modes);
    renderWatchlist(payload.watchlist || []);
    setMindsetText(payload.mindset || {});
    updateReadiness(payload.readiness);
    renderPanels(payload.panels);
    renderTabs(payload.advanced_tabs);
    renderChart(payload.chart);
    document.getElementById("chart-subtitle").textContent = `${payload.symbol} • ${payload.timeframe}`;
  } catch (error) {
    console.error(error);
    alert("Failed to load signals. Please try again later.");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setupAlertDrawer();
  const { symbol, mode } = getParams();
  loadSignals(symbol, mode);
});
