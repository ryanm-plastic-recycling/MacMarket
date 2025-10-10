(() => {
  const state = {
    chart: null,
    candleSeries: null,
    sma20Series: null,
    sma50Series: null,
    trendSeries: null,
    mini: { haco: null, hacolt: null },
    haco: { main: null, candle: null, miniHaco: null, miniHacolt: null },
    resizeObs: null,
    tabs: [],
    activeTab: null,
    lastMode: 'swing',

    // UI toggles (top section)
    toggles: {
      topHacoStrip: true,
      topHacoltStrip: true,
      topHacoArrows: true,
      topSma20: true,
      topSma50: true,
      topTrend: true,
    },

    // cache last markers so we can re-apply quickly when toggling HACO arrows
    _lastTopMarkers: [],
  };

  const el = (id) => document.getElementById(id);

  function setStatus(message, tone = 'info') {
    const node = el('status');
    if (!node) return;
    node.textContent = message;
    node.dataset.tone = tone;
  }

  // ---------- Resize ----------
  function resizeChart() {
    const hostTop = document.getElementById('signals-chart');
    if (hostTop && state.chart) {
      const w = Math.max(320, hostTop.clientWidth || hostTop.offsetWidth || 0);
      const h = Math.max(300, hostTop.clientHeight || 360);
      state.chart.resize(w, h);
    }
    // minis follow width
    ['mini-haco', 'mini-hacolt'].forEach(id => {
      const host = document.getElementById(id);
      const obj = id === 'mini-haco' ? state.mini.haco : state.mini.hacolt;
      if (host && obj?.chart) obj.chart.resize(host.clientWidth || 0, host.clientHeight || 64);
    });
    // HACO main
    const hhost = document.getElementById('haco-chart');
    if (hhost && state.haco.main) {
      state.haco.main.resize(hhost.clientWidth || 0, hhost.clientHeight || 420);
    }
    // HACO minis
    ['haco-mini-haco', 'haco-mini-hacolt'].forEach(id => {
      const host = document.getElementById(id);
      const obj = (id === 'haco-mini-haco') ? state.haco.miniHaco : state.haco.miniHacolt;
      if (host && obj?.chart) obj.chart.resize(host.clientWidth || 0, host.clientHeight || 64);
    });
  }

  // ---------- HACO arrow helpers ----------
  // Build markers (up/down arrows) from HACO series aligned to candle times
  function buildHacoMarkers(candles, hacoPoints) {
    const byTime = new Map((hacoPoints || []).map(p => [Number(p.time), p.value]));
    const markers = [];
    for (const c of candles || []) {
      const t = Number(c.time);
      const v = byTime.get(t);
      if (v === 100) {
        markers.push({
          time: t,
          position: 'belowBar',
          color: '#16a34a',
          shape: 'arrowUp',
          text: 'HACO',
        });
      } else if (v === 0) {
        markers.push({
          time: t,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: 'HACO',
        });
      }
    }
    return markers;
  }

  function applyTopArrowsVisible(visible) {
    if (!state.candleSeries) return;
    if (visible) {
      state.candleSeries.setMarkers(state._lastTopMarkers || []);
    } else {
      state.candleSeries.setMarkers([]);
    }
  }

  // ---------- Top toggles UI ----------
  function ensureTopToggleUI() {
    if (document.getElementById('chart-toggles')) return;

    const chartCol = document.querySelector('#signals-top .chart-col');
    if (!chartCol) return;

    const wrap = document.createElement('div');
    wrap.id = 'chart-toggles';
    wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px;align-items:center;font-size:.9rem;';
    wrap.innerHTML = `
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-haco" checked> HACO strip
      </label>
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-hacolt" checked> HACOLT strip
      </label>
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-arrows" checked> HACO arrows
      </label>
      <span style="width:12px;"></span>
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-sma20" checked> SMA 20
      </label>
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-sma50" checked> SMA 50
      </label>
      <label style="display:flex;gap:6px;align-items:center;">
        <input type="checkbox" id="tg-top-trend" checked> Trend line
      </label>
    `;
    chartCol.prepend(wrap);

    // Wire events
    const q = (id) => document.getElementById(id);

    q('tg-top-haco').addEventListener('change', (e) => {
      state.toggles.topHacoStrip = !!e.target.checked;
      const host = document.getElementById('mini-haco');
      if (host) host.style.display = state.toggles.topHacoStrip ? '' : 'none';
    });

    q('tg-top-hacolt').addEventListener('change', (e) => {
      state.toggles.topHacoltStrip = !!e.target.checked;
      const host = document.getElementById('mini-hacolt');
      if (host) host.style.display = state.toggles.topHacoltStrip ? '' : 'none';
    });

    q('tg-top-arrows').addEventListener('change', (e) => {
      state.toggles.topHacoArrows = !!e.target.checked;
      applyTopArrowsVisible(state.toggles.topHacoArrows);
    });

    q('tg-top-sma20').addEventListener('change', (e) => {
      state.toggles.topSma20 = !!e.target.checked;
      state.sma20Series?.applyOptions({ visible: state.toggles.topSma20 });
    });

    q('tg-top-sma50').addEventListener('change', (e) => {
      state.toggles.topSma50 = !!e.target.checked;
      state.sma50Series?.applyOptions({ visible: state.toggles.topSma50 });
    });

    q('tg-top-trend').addEventListener('change', (e) => {
      state.toggles.topTrend = !!e.target.checked;
      state.trendSeries?.applyOptions({ visible: state.toggles.topTrend });
    });
  }

  // ---------- Minis (top + haco) ----------
  function ensureMini(id) {
    const host = document.getElementById(id);
    if (!host || typeof LightweightCharts === 'undefined') return null;
    const chart = LightweightCharts.createChart(host, {
      height: host.clientHeight || 64,
      layout: { background: { color: 'transparent' }, textColor: '#d7dee7' },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
      timeScale: {
        borderVisible: false,
        fixLeftEdge: false,
        fixRightEdge: false,
        rightBarStaysOnScroll: false,
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addHistogramSeries({ priceScaleId: '' });
    return { chart, series };
  }

  // (kept your two-way logical link helper; minis are still passive so this won’t fight)
  function syncTime(scopedCharts) {
    const [main, ...others] = scopedCharts;
    if (!main) return;
    const syncTo = (src, dst) => {
      src.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!range) return;
        try { dst.timeScale().setVisibleLogicalRange(range); } catch {}
      });
    };
    others.forEach(o => { syncTo(main, o); syncTo(o, main); });
  }

  function linkMasterToSlaves(master, slaves) {
    if (!master || !slaves?.length) return;
    let syncing = false;
    const applyTimeRange = (range) => {
      if (!range || syncing) return;
      syncing = true;
      try { slaves.forEach(s => s.timeScale().setVisibleRange(range)); }
      finally { syncing = false; }
    };
    const applyLogicalRange = (range) => {
      if (!range || syncing) return;
      syncing = true;
      try { slaves.forEach(s => s.timeScale().setVisibleLogicalRange(range)); }
      finally { syncing = false; }
    };
    master.timeScale().subscribeVisibleTimeRangeChange(applyTimeRange);
    master.timeScale().subscribeVisibleLogicalRangeChange(applyLogicalRange);
  }

  // ---------- HACO Strategy section ----------
  function ensureHacoCharts() {
    const host = document.getElementById('haco-chart');
    if (!host || typeof LightweightCharts === 'undefined') return null;

    if (!state.haco.main) {
      state.haco.main = LightweightCharts.createChart(host, {
        height: host.clientHeight || 420,
        layout: { background: { color: 'transparent' }, textColor: '#d7dee7' },
        rightPriceScale: { visible: false },
        leftPriceScale:  { visible: false },
        timeScale: { borderVisible: false, rightOffset: 0 },
        grid: { vertLines: { color: 'rgba(70, 70, 70, 0.2)' }, horzLines: { color: 'rgba(70, 70, 70, 0.2)' } },
      });
      state.haco.candle = state.haco.main.addCandlestickSeries({
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350',
      });

      state.haco.miniHaco   = ensureMini('haco-mini-haco');
      state.haco.miniHacolt = ensureMini('haco-mini-hacolt');
      const hacoSlaves = [state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
      linkMasterToSlaves(state.haco.main, hacoSlaves);

      // optional: also keep two-way logical link (minis are passive anyway)
      const chartsToSync = [state.haco.main, state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
      syncTime(chartsToSync);
    }
    return state.haco.main;
  }

  function ensureHacoMinis() {
    if (!state.haco.miniHaco)   state.haco.miniHaco   = ensureMini('haco-mini-haco');
    if (!state.haco.miniHacolt) state.haco.miniHacolt = ensureMini('haco-mini-hacolt');

    if (!state.haco.main && window.HACO && window.HACO.chart) {
      state.haco.main = window.HACO.chart;
    }

    if (!state.haco.main) {
      window.addEventListener('haco:ready', (e) => {
        if (e?.detail?.chart) {
          state.haco.main = e.detail.chart;
          const chartsToSync = [state.haco.main, state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
          syncTime(chartsToSync);
          const hacoSlaves = [state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
          linkMasterToSlaves(state.haco.main, hacoSlaves);
        }
      }, { once: true });
    } else {
      const chartsToSync = [state.haco.main, state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
      syncTime(chartsToSync);
      const hacoSlaves = [state.haco.miniHaco?.chart, state.haco.miniHacolt?.chart].filter(Boolean);
      linkMasterToSlaves(state.haco.main, hacoSlaves);
    }
  }

  function toMiniBars(series) {
    return (series || []).map(p => {
      let color = '#64748b';           // 50 = neutral
      if (p.value === 100) color = '#16a34a';   // up
      else if (p.value === 0) color = '#ef4444'; // down
      return { time: Number(p.time), value: p.value || 0, color };
    });
  }

  function renderHacoSection(chartPayload) {
    ensureHacoCharts();
    ensureHacoMinis();
    if (!chartPayload) return;

    const hacoBars   = toMiniBars(chartPayload.haco);
    const hacoltBars = toMiniBars(chartPayload.hacolt);

    if (state.haco.miniHaco?.series)   state.haco.miniHaco.series.setData(hacoBars.length ? hacoBars : []);
    if (state.haco.miniHacolt?.series) state.haco.miniHacolt.series.setData(hacoltBars.length ? hacoltBars : []);
  }

  // ---------- Top chart ----------
  function ensureChart() {
    const container = el('signals-chart');
    if (!container || typeof LightweightCharts === 'undefined') return null;
    if (!state.chart) {
      state.chart = LightweightCharts.createChart(container, {
        height: 360,
        layout: { background: { color: 'transparent' }, textColor: '#d7dee7' },
        rightPriceScale: { visible: false },    // no gutter to the right
        leftPriceScale:  { visible: false },
        timeScale: { borderVisible: false, rightOffset: 0 },
        grid: { vertLines: { color: 'rgba(70, 70, 70, 0.2)' }, horzLines: { color: 'rgba(70, 70, 70, 0.2)' } },
      });
      state.candleSeries = state.chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
      state.sma20Series = state.chart.addLineSeries({ color: '#4c78ff', lineWidth: 2 });
      state.sma50Series = state.chart.addLineSeries({ color: '#ffa600', lineWidth: 2 });
      state.trendSeries = state.chart.addLineSeries({
        color: '#ab47bc',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dotted,
      });

      // minis create + range link
      if (!state.mini.haco)   state.mini.haco   = ensureMini('mini-haco');
      if (!state.mini.hacolt) state.mini.hacolt = ensureMini('mini-hacolt');
      const slaves = [state.mini.haco?.chart, state.mini.hacolt?.chart].filter(Boolean);
      linkMasterToSlaves(state.chart, slaves);
      // optional logical link (minis are passive anyway)
      const chartsToSync = [state.chart, state.mini.haco?.chart, state.mini.hacolt?.chart].filter(Boolean);
      syncTime(chartsToSync);

      // toggles UI
      ensureTopToggleUI();

      // Initial resize + observers
      resizeChart();
      window.addEventListener('resize', resizeChart);
      if ('ResizeObserver' in window) {
        state.resizeObs?.disconnect();
        state.resizeObs = new ResizeObserver(() => resizeChart());
        state.resizeObs.observe(container);
      }
    }
    return state.chart;
  }

  function renderChart(chartPayload) {
    const chart = ensureChart();
    if (!chart || !chartPayload) return;

    const candles = (chartPayload.candles || []).map((c) => ({
      time: Number(c.time),
      open: c.o,
      high: c.h,
      low: c.l,
      close: c.c,
    }));
    state.candleSeries.setData(candles);

    // minis
    const hacoBars   = toMiniBars(chartPayload.haco);
    const hacoltBars = toMiniBars(chartPayload.hacolt);
    if (state.mini.haco?.series)   state.mini.haco.series.setData(hacoBars.length ? hacoBars : []);
    if (state.mini.hacolt?.series) state.mini.hacolt.series.setData(hacoltBars.length ? hacoltBars : []);
    // apply visibility from toggles
    const hostHaco   = document.getElementById('mini-haco');
    const hostHacolt = document.getElementById('mini-hacolt');
    if (hostHaco)   hostHaco.style.display   = state.toggles.topHacoStrip   ? '' : 'none';
    if (hostHacolt) hostHacolt.style.display = state.toggles.topHacoltStrip ? '' : 'none';

    // indicators
    const indicators = chartPayload.indicators || {};
    state.sma20Series.setData((indicators.sma20 || []).map((p) => ({ time: Number(p.time), value: p.value })));
    state.sma50Series.setData((indicators.sma50 || []).map((p) => ({ time: Number(p.time), value: p.value })));
    state.trendSeries.setData((indicators.trend || []).map((p) => ({ time: Number(p.time), value: p.value })));
    state.sma20Series.applyOptions({ visible: state.toggles.topSma20 });
    state.sma50Series.applyOptions({ visible: state.toggles.topSma50 });
    state.trendSeries.applyOptions({ visible: state.toggles.topTrend });

    // HACO arrows on top chart
    state._lastTopMarkers = buildHacoMarkers(candles, chartPayload.haco || []);
    applyTopArrowsVisible(state.toggles.topHacoArrows);

    resizeChart();
  }

  // ---------- Legacy/other UI (unchanged) ----------
  function renderReadiness(readiness) {
    const scoreEl = el('readiness-score');
    const componentsEl = el('readiness-components');
    if (!scoreEl || !componentsEl) return;
    const score = readiness?.score ?? 0;
    scoreEl.textContent = Math.round(score);
    scoreEl.style.setProperty('--score', score);
    scoreEl.classList.remove('is-weak', 'is-neutral', 'is-strong');
    if (score >= 60) scoreEl.classList.add('is-strong');
    else if (score >= 40) scoreEl.classList.add('is-neutral');
    else scoreEl.classList.add('is-weak');

    componentsEl.innerHTML = '';
    (readiness?.components || []).forEach((comp) => {
      const item = document.createElement('li');
      item.innerHTML = `<span>${comp.title}</span><strong>${Math.round(comp.score)}</strong><small>${comp.status}</small>`;
      componentsEl.appendChild(item);
    });
  }

  function renderPanels(panels) {
    const grid = el('panels-grid');
    if (!grid) return;
    grid.innerHTML = '';
    (panels || []).forEach((panel) => {
      const card = document.createElement('article');
      card.className = 'panel-card';
      const bar = document.createElement('div');
      bar.className = 'bar';
      const span = document.createElement('span');
      bar.appendChild(span);
      card.innerHTML = `
        <header>
          <h4>${panel.title}</h4>
          <span class="badge">${Math.round(panel.score)}</span>
        </header>
        <p>${panel.summary || panel.reason || ''}</p>
        <small>${panel.goal || ''}</small>
        <footer>${panel.status || ''}</footer>
      `;
      card.querySelector('p').after(bar);
      span.style.width = `${Math.max(0, Math.min(100, panel.score || 0))}%`;
      bar.style.setProperty('--goal-pct', `${Math.max(0, Math.min(100, panel.goal_pct || 60))}%`);
      grid.appendChild(card);
    });
  }

  function renderEntries(entries) {
    const list = el('entries-list');
    if (!list) return;
    list.innerHTML = '';
    (entries || []).forEach((entry) => {
      const li = document.createElement('li');
      const confidence = entry.confidence != null ? `${Math.round(entry.confidence)}%` : '—';
      li.innerHTML = `
        <strong>${entry.type ?? 'neutral'}</strong>
        <span>${entry.summary ?? ''}</span>
        <em>${confidence}</em>`;
      list.appendChild(li);
    });
  }

  function renderExits(exits) {
    const container = el('exits-summary');
    if (!container) return;
    container.innerHTML = '';
    if (!exits || !exits.levels) {
      container.textContent = exits?.reason || 'No exit data available.';
      return;
    }

    const table = document.createElement('table');
    table.className = 'levels-table';
    const header = document.createElement('tr');
    header.innerHTML = '<th>Risk</th><th>Level</th>';
    table.appendChild(header);
    Object.entries(exits.levels).forEach(([risk, value]) => {
      const row = document.createElement('tr');
      row.innerHTML = `<td>${risk}</td><td>${value ?? '—'}</td>`;
      table.appendChild(row);
    });
    container.appendChild(table);
    const reason = document.createElement('p');
    reason.className = 'muted';
    reason.textContent = exits.reason ?? '';
    container.appendChild(reason);
  }

  function renderAdvancedTabs(tabs) {
    const nav = el('advanced-tabs-nav');
    const content = el('advanced-tab-content');
    if (!nav || !content) return;
    nav.innerHTML = '';
    content.innerHTML = '';
    state.tabs = tabs || [];
    if (!state.tabs.length) {
      content.textContent = 'No advanced notes for this mode.';
      return;
    }
    state.tabs.forEach((tab, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = tab.title || tab.id;
      btn.dataset.tabId = tab.id;
      if (index === 0) {
        btn.classList.add('active');
        state.activeTab = tab.id;
      }
      btn.addEventListener('click', () => activateTab(tab.id));
      nav.appendChild(btn);
    });
    activateTab(state.tabs[0].id);
  }

  function activateTab(tabId) {
    const content = el('advanced-tab-content');
    const nav = el('advanced-tabs-nav');
    if (!content || !nav) return;
    state.activeTab = tabId;
    [...nav.querySelectorAll('button')].forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tabId === tabId);
    });
    const tab = state.tabs.find(t => t.id === tabId) || state.tabs[0];
    content.innerHTML = '';
    if (!tab) return;
    const items = Array.isArray(tab.content) ? tab.content : [tab.content];
    const list = document.createElement('ul');
    items.filter(Boolean).forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      list.appendChild(li);
    });
    content.appendChild(list);
  }

  function findTab(id) {
    return state.tabs.find((tab) => tab.id === id) || state.tabs[0];
  }

  function renderMindset(mindset) {
    const taglineEl = el('mindset-tagline');
    const focusEl = el('mindset-focus');
    if (taglineEl) taglineEl.textContent = mindset?.tagline || '';
    if (focusEl) {
      focusEl.innerHTML = '';
      (mindset?.focus || []).forEach((point) => {
        const li = document.createElement('li');
        li.textContent = point;
        focusEl.appendChild(li);
      });
    }
  }

  function renderWatchlist(watchlist) {
    const list = el('watchlist-list');
    if (!list) return;
    list.innerHTML = '';
    (watchlist || []).forEach((symbol) => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = symbol;
      btn.addEventListener('click', () => {
        const symbolInput = el('symbol');
        if (symbolInput) symbolInput.value = symbol;
        runSignal();
      });
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  function renderModes(modes, selected) {
    const select = el('mode-select');
    if (!select) return;
    const normalized = (modes || []).map((mode) => mode.toLowerCase());
    const current = new Set();
    select.innerHTML = '';
    normalized.forEach((mode) => {
      const option = document.createElement('option');
      option.value = mode;
      option.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
      if (mode === selected) option.selected = true;
      current.add(mode);
      select.appendChild(option);
    });
    if (!current.has(selected) || !selected) {
      const fallback = document.createElement('option');
      fallback.value = 'swing';
      fallback.textContent = 'Swing';
      fallback.selected = true;
      select.appendChild(fallback);
    }
    state.lastMode = select.value || 'swing';
  }

  function applyLegacySections(data) {
    const newsEl = el('news-output');
    const techEl = el('tech-output');
    if (newsEl) {
      newsEl.className = '';
      const score = data?.news?.score ?? 0;
      newsEl.textContent = `Score: ${score}`;
      if (score > 0) newsEl.classList.add('bullish');
      else if (score < 0) newsEl.classList.add('bearish');
    }
    if (techEl) {
      techEl.className = '';
      const signal = data?.technical?.signal ?? 'none';
      techEl.textContent = signal;
      if (signal === 'bullish') techEl.classList.add('bullish');
      else if (signal === 'bearish') techEl.classList.add('bearish');
    }
  }

  // ---------- Fetch/boot ----------
  async function fetchSignal() {
    const symbolInput = el('symbol');
    const modeSelect = el('mode-select');
    if (!symbolInput) return null;
    const sym = symbolInput.value.trim().toUpperCase();
    if (!sym) return null;
    let mode = (modeSelect && modeSelect.value) ? modeSelect.value.trim().toLowerCase() : (state.lastMode || 'swing');
    if (!mode) mode = 'swing';
    setStatus(`Loading ${sym} (${mode}) signal...`, 'loading');
    try {
      const res = await fetch(`/api/signals/${encodeURIComponent(sym)}?mode=${encodeURIComponent(mode)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderModes(data.available_modes || [], data.mode || mode);
      renderReadiness(data.readiness);
      renderPanels(data.panels);
      renderChart(data.chart);
      renderHacoSection(data.chart);
      renderChecklist(data.panels, data.readiness, data.meta);

      // chart subtitle chips
      const subtitle = document.getElementById('chart-subtitle') || document.createElement('span');
      subtitle.id = 'chart-subtitle';
      const meta = data.meta || {};
      const trendChip = meta.trend_pass ? 'Trend: PASS' : 'Trend: FAIL';
      const adxChip   = (meta.adx != null && meta.adx < 25) ? `Chop (ADX ${meta.adx.toFixed(1)})` : `ADX ${meta.adx?.toFixed?.(1) ?? ''}`;
      let hacoltChip = '';
      if (meta.hacolt_now === 100) hacoltChip = 'LT Up';
      else if (meta.hacolt_now === 0) hacoltChip = 'LT Down';
      subtitle.textContent = [trendChip, adxChip, hacoltChip].filter(Boolean).join(' • ');

      const chartCol = document.querySelector('#signals-top .chart-col') || document.querySelector('.overview-chart');
      if (chartCol && !document.getElementById('chart-subtitle')) {
        const h = document.createElement('div');
        h.style.margin = '6px 0 8px';
        h.id = 'chart-subtitle';
        h.textContent = subtitle.textContent;
        chartCol.prepend(h);
      } else if (document.getElementById('chart-subtitle')) {
        document.getElementById('chart-subtitle').textContent = subtitle.textContent;
      }

      renderEntries(data.entries);
      renderExits(data.exits);
      renderAdvancedTabs(data.advanced_tabs);
      renderMindset(data.mindset);
      renderWatchlist(data.watchlist);
      applyLegacySections(data);
      setStatus('Signal updated', 'ok');
      return data;
    } catch (err) {
      console.error(err);
      setStatus('Failed to load signal', 'error');
      return null;
    }
  }

  function renderHacoltBars(series) {
    const host = document.getElementById('haco-signal-chart');
    if (!host) return;
    const width = host.clientWidth || 600;
    const height = host.clientHeight || 100;
    host.innerHTML = '';
    const canvas = document.createElement('canvas');
    canvas.width = width; canvas.height = height;
    host.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const n = series.length || 0;
    if (!n) return;
    const w = width / n;
    for (let i=0;i<n;i++){
      const v = series[i].value;
      ctx.fillStyle = v === 100 ? '#16a34a' : v === 0 ? '#ef4444' : '#64748b';
      ctx.fillRect(i*w, 0, Math.ceil(w), height);
    }
  }

  function renderChecklist(panels, readiness, meta) {
    const container = document.getElementById('advanced-tab-content');
    if (!container) return;
    const byId = Object.fromEntries((panels||[]).map(p => [p.id, p]));
    const pass = id => (byId[id]?.status === 'PASS');
    const ready = Math.round(readiness?.score || 0);
    const items = [
      {label:'Trend PASS', ok: pass('trend')},
      {label:'Momentum PASS', ok: pass('momentum')},
      {label:'Volatility PASS', ok: pass('volatility')},
      {label:'Volume PASS or improving', ok: pass('volume')},
      {label:'HACOLT = 100 (optional long bias)', ok: (meta?.hacolt_now === 100)},
      {label:`Readiness ≥ 75 (now ${ready})`, ok: ready >= 75},
    ];
    const html = items.map(i => `<li>${i.ok ? '✅' : '⬜'} ${i.label}</li>`).join('');
    const wrap = document.createElement('div');
    wrap.style.marginTop = '10px';
    wrap.innerHTML = `<h4>Checklist</h4><ul>${html}</ul>`;
    container.appendChild(wrap);
  }

  function sma(values, period) {
    const res = [];
    let sum = 0;
    for (let i = 0; i < values.length; i += 1) {
      sum += values[i];
      if (i >= period) sum -= values[i - period];
      res.push(i >= period - 1 ? sum / period : null);
    }
    return res;
  }

  function findLastCross(shortArr, longArr) {
    for (let i = shortArr.length - 1; i > 0; i -= 1) {
      if (
        shortArr[i] == null ||
        longArr[i] == null ||
        shortArr[i - 1] == null ||
        longArr[i - 1] == null
      )
        continue;
      if (shortArr[i - 1] < longArr[i - 1] && shortArr[i] > longArr[i]) return { index: i, dir: 'up' };
      if (shortArr[i - 1] > longArr[i - 1] && shortArr[i] < longArr[i]) return { index: i, dir: 'down' };
    }
    return null;
  }

  async function renderTechChart(sym) {
    try {
      const res = await fetch(`/api/history?symbol=${encodeURIComponent(sym)}&period=6mo&interval=1d`);
      if (!res.ok) return;
      const hist = await res.json();
      const dates = hist.dates;
      const closes = hist.close;
      const ma20 = sma(closes, 20);
      const ma50 = sma(closes, 50);
      const chartEl = el('tech-chart');
      if (!chartEl || typeof LightweightCharts === 'undefined') return;
      chartEl.innerHTML = '';
      const chart = LightweightCharts.createChart(chartEl, { height: 300 });
      const priceSeries = chart.addLineSeries({ color: '#4c78ff' });
      const ma20Series = chart.addLineSeries({ color: 'green' });
      const ma50Series = chart.addLineSeries({ color: 'red' });
      const priceData = dates.map((d, i) => ({ time: d, value: closes[i] }));
      priceSeries.setData(priceData);
      ma20Series.setData(dates.map((d, i) => (ma20[i] ? { time: d, value: ma20[i] } : null)).filter(Boolean));
      ma50Series.setData(dates.map((d, i) => (ma50[i] ? { time: d, value: ma50[i] } : null)).filter(Boolean));
      const cross = findLastCross(ma20, ma50);
      if (cross) {
        priceSeries.setMarkers([{
          time: dates[cross.index],
          position: cross.dir === 'up' ? 'belowBar' : 'aboveBar',
          color: cross.dir === 'up' ? 'green' : 'red',
          shape: cross.dir === 'up' ? 'arrowUp' : 'arrowDown',
          text: '20/50',
        }]);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchMacro() {
    const text = el('macro-text')?.value;
    if (!text) return;
    setStatus('Analyzing macro...', 'loading');
    const res = await fetch('/api/macro-signal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      setStatus('Macro analysis failed', 'error');
      return;
    }
    const data = await res.json();
    const output = el('macro-output');
    if (output) output.textContent = data.outlook;
    setStatus('Macro analysis complete', 'ok');
  }

  async function fetchRecs() {
    const userId = localStorage.getItem('userId');
    if (!userId) return;
    setStatus('Loading recommendations...', 'loading');
    const res = await fetch(`/api/users/${userId}/recommendations`);
    if (!res.ok) {
      setStatus('Failed to load recommendations', 'error');
      return;
    }
    const data = await res.json();
    const body = document.querySelector('#recs-table tbody');
    if (!body) return;
    body.innerHTML = '';
    (data.recommendations || []).forEach((r) => {
      const tr = document.createElement('tr');
      const exit = (r.exit_price != null) ? Number(r.exit_price).toFixed(2) : '';
      const prob = `${Math.round((r.probability || 0) * 100)}%`;
      tr.innerHTML = `<td>${r.symbol}</td><td>${r.action}</td><td>${exit}</td><td>${prob}</td><td>${r.reason}</td>`;
      body.appendChild(tr);
    });
    setStatus('Recommendations loaded', 'ok');
  }

  async function fetchSingle() {
    const sym = el('symbol')?.value.trim().toUpperCase();
    if (!sym) return;
    const res = await fetch(`/api/recommendation/${encodeURIComponent(sym)}`);
    if (!res.ok) return;
    const data = await res.json();
    const body = document.querySelector('#single-rec tbody');
    if (!body || !data.recommendation) return;
    body.innerHTML = '';
    const r = data.recommendation;
    const exit = (r.exit_price != null) ? Number(r.exit_price).toFixed(2) : '';
    const prob = `${Math.round((r.probability || 0) * 100)}%`;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.symbol}</td><td>${r.action}</td><td>${exit}</td><td>${prob}</td><td>${r.reason}</td>`;
    body.appendChild(tr);
  }

  function runSignal() {
    Promise.allSettled([fetchSignal(), fetchSingle()]);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const getSignalBtn = el('get-signal');
    const macroBtn = el('run-macro');
    const recsBtn = el('get-recs');
    const symbolInput = el('symbol');
    const modeSelect = el('mode-select');
    const adminLink = el('admin-link');

    if (adminLink && localStorage.getItem('isAdmin') === '1') {
      adminLink.style.display = 'block';
    }

    if (getSignalBtn) getSignalBtn.addEventListener('click', () => runSignal());
    if (macroBtn) macroBtn.addEventListener('click', fetchMacro);
    if (recsBtn) recsBtn.addEventListener('click', fetchRecs);
    if (symbolInput) {
      symbolInput.addEventListener('input', (event) => {
        event.target.value = event.target.value.toUpperCase();
      });
    }
    if (modeSelect) {
      modeSelect.addEventListener('change', () => runSignal());
    }

    runSignal();
  });
})();
