// /static/js/haco-ui.js
(function () {
  // ===== Time-scale alignment helper for HACO charts =====
  // Keeps two Lightweight Charts in perfect horizontal (time) alignment by syncing
  // visible *logical* range in both directions, with an initial normalization.
  function linkTimeScales(chartA, chartB) {
    if (!chartA || !chartB) return;
    // Normalize key time options to reduce drift
    chartA.applyOptions({ timeScale: { timeVisible: true, secondsVisible: false }});
    chartB.applyOptions({ timeScale: { timeVisible: true, secondsVisible: false }});
    let syncing = false;
    const sync = (src, dst) => () => {
      if (syncing) return;
      syncing = true;
      const range = src.timeScale().getVisibleLogicalRange();
      if (range) dst.timeScale().setVisibleLogicalRange(range);
      syncing = false;
    };
    chartA.timeScale().subscribeVisibleLogicalRangeChange(sync(chartA, chartB));
    chartB.timeScale().subscribeVisibleLogicalRangeChange(sync(chartB, chartA));
    // Initial alignment after data/size settle
    setTimeout(() => {
      try {
        chartA.timeScale().fitContent();
        chartB.timeScale().fitContent();
        const r = chartA.timeScale().getVisibleLogicalRange();
        if (r) chartB.timeScale().setVisibleLogicalRange(r);
      } catch(e) { console.warn('[HACO] linkTimeScales init:', e); }
    }, 0);
  }
  window.HACOSync = { linkTimeScales };

  // ===== HACO big-arrow overlay helper (HTML overlay, non-blocking) =====
  const HACOOverlay = (function () {
    function ensureOverlay(container) {
      let el = container.querySelector('.haco-overlay');
      if (!el) {
        el = document.createElement('div');
        el.className = 'haco-overlay';
        container.appendChild(el); // never touch container.innerHTML
      }
      el.style.background = 'transparent';
      el.style.pointerEvents = 'none';
      return el;
    }

    function computeMarkersFromBars(bars) {
      const out = [];
      for (const b of (bars || [])) {
        if (b?.upw) out.push({ time: b.time, price: b.low ?? b.close, dir: 'up' });
        if (b?.dnw) out.push({ time: b.time, price: b.high ?? b.close, dir: 'down' });
      }
      return out;
    }

    function placeArrow({ chart, series, overlay, m }) {
      const x = chart.timeScale().timeToCoordinate(m.time);
      const y = series.priceToCoordinate(m.price);
      if (x == null || y == null) return;
      const el = document.createElement('div');
      el.className = `haco-arrow ${m.dir}`;
      el.textContent = m.dir === 'up' ? '▲' : '▼';
      el.style.transform = `translate(${x}px, ${y}px)`;
      overlay.appendChild(el);
    }

    function attach({ container, chart, series, bars, markers }) {
      if (!container || !chart || !series) return;
      const overlay = ensureOverlay(container);
      let data = Array.isArray(markers) ? markers : computeMarkersFromBars(bars);
      if (!Array.isArray(data)) data = [];

      const redraw = () => {
        overlay.innerHTML = '';
        for (const m of data) placeArrow({ chart, series, overlay, m });
      };

      const ro = new ResizeObserver(() => requestAnimationFrame(redraw));
      ro.observe(container);
      chart.timeScale().subscribeVisibleTimeRangeChange(() => requestAnimationFrame(redraw));
      setTimeout(redraw, 0);
      setTimeout(redraw, 50);

      return {
        updateMarkers(next) { data = Array.isArray(next) ? next : data; redraw(); },
        redraw,
      };
    }

    return { attach };
  })();

  window.HACOOverlay = HACOOverlay;
})();

// ===== Signal sub-chart: create once if the element exists (feature-detected series) =====
(function () {
  const signalChartEl = document.getElementById('haco-signal-chart');
  if (!signalChartEl) return;

  const LW = window.LightweightCharts;
  if (!LW || typeof LW.createChart !== 'function') return;

  if (!signalChartEl.__signalChart) {
    signalChartEl.textContent = '';
    const api = LW.createChart(signalChartEl, {
      height: 100,
      timeScale: { visible: false },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
    });

    let series = null;
    if (typeof api.addHistogramSeries === 'function') {
      series = api.addHistogramSeries({
        priceScaleId: '',
        priceFormat: { type: 'price', precision: 0, minMove: 1 },
      });
      if (series?.priceScale) {
        series.priceScale().applyOptions({ scaleMargins: { top: 0, bottom: 0 } });
      }
    } else if (typeof api.addLineSeries === 'function') {
      console.warn('[HACO] addHistogramSeries not available; using line series fallback for signal chart.');
      series = api.addLineSeries({ priceScaleId: '' });
    } else if (typeof api.addAreaSeries === 'function') {
      console.warn('[HACO] No histogram/line; using area series fallback for signal chart.');
      series = api.addAreaSeries({ priceScaleId: '' });
    } else {
      console.warn('[HACO] No histogram/line/area series available; skipping signal chart.');
      Object.defineProperty(signalChartEl, '__signalChart', { value: api, writable: false });
      window.__setSignalData = () => {}; // no-op to avoid later errors
      return;
    }

    Object.defineProperties(signalChartEl, {
      __signalChart: { value: api, writable: false },
      __signalSeries: { value: series, writable: false },
      __signalKind: { value: (series && series.setData) ? 'ok' : 'none', writable: false },
    });
  }

  // Setter used by renderChart()
  window.__setSignalData = (bars) => {
    const series = signalChartEl.__signalSeries;
    if (!series || typeof series.setData !== 'function') return;
    const data = (bars || []).map((b) => ({
      time: normalizeTime(b.time),
      value: 1,
      color: b.state ? '#2ecc71' : '#e74c3c',
    }));
    // Some series types ignore color per point; that's fine as a fallback.
    series.setData(data.map(d => ({ time: d.time, value: d.value, color: d.color })));
    signalChartEl.__signalChart.timeScale().fitContent();
  };

  // Expose getter so we can wire up pan/zoom sync from the main chart
  window.__getSignalChart = () => signalChartEl.__signalChart || null;
})();

// ===== Pan/zoom synchronization between two Lightweight Charts =====

async function fetchHaco() {
  const symbol = document.getElementById('haco-symbol').value.trim();
  const timeframe = document.getElementById('haco-timeframe').value.trim();
  const lenUp = document.getElementById('haco-lenUp').value;
  const lenDown = document.getElementById('haco-lenDown').value;
  const alertLookback = document.getElementById('haco-alertLookback').value;
  const lookback = document.getElementById('haco-lookback').value;
  const url = `/api/signals/haco?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(
    timeframe
  )}&lengthUp=${lenUp}&lengthDown=${lenDown}&alertLookback=${alertLookback}&lookback=${lookback}`;

  const res = await fetch(url);
  if (!res.ok) {
    alert('No data');
    return;
  }
  const data = await res.json();
  renderChart(data.series || []);
  explainLast(data.last || {});
}

function normalizeTime(t) {
  // Lightweight Charts expects seconds if numeric. Convert ms → sec if needed.
  if (typeof t === 'number' && t > 2_000_000_000) return Math.floor(t / 1000);
  return t;
}

function renderChart(bars) {
  console.debug('[HACO] renderChart bars length:', Array.isArray(bars) ? bars.length : '(not array)');
  const LW = window.LightweightCharts;
  if (!LW || typeof LW.createChart !== 'function') {
    console.error('[HACO] LightweightCharts not loaded or createChart missing');
    return;
  }

  const chartEl = document.getElementById('haco-chart');
  if (!chartEl) {
    console.error('[HACO] #haco-chart container not found');
    return;
  }

  // Create the main chart once and cache API/series on the container
  if (!chartEl.__hacoChart) {
    chartEl.textContent = '';

    const api = LW.createChart(chartEl, {
      height: 400,
      layout: { background: { color: 'transparent' } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });

    const price = (typeof api.addCandlestickSeries === 'function')
      ? api.addCandlestickSeries({
          upColor: '#26a69a',
          downColor: '#ef5350',
          borderVisible: false,
          wickUpColor: '#26a69a',
          wickDownColor: '#ef5350',
        })
      : (typeof api.addAreaSeries === 'function'
          ? api.addAreaSeries({})
          : null);

    Object.defineProperties(chartEl, {
      __hacoChart: { value: api, writable: false },
      __hacoPrice: { value: price, writable: false },
    });

    console.debug('[HACO] series methods on main chart',
      typeof api.addCandlestickSeries,
      typeof api.addLineSeries,
      typeof api.addAreaSeries
    );
  }

  const chartApi = chartEl.__hacoChart;
  const priceSeries = chartEl.__hacoPrice;

  if (!chartApi || (typeof chartApi.timeScale !== 'function')) {
    console.error('[HACO] Unexpected chart object:', chartApi);
    return;
  }
  if (!priceSeries || typeof priceSeries.setData !== 'function') {
    console.error('[HACO] Price series not available on this build.');
    return;
  }

  // Update sub-chart (if present)
  if (typeof window.__setSignalData === 'function') {
    window.__setSignalData(bars);
  }

  // Candles/area data (normalize time)
  const candles = (bars || []).map((b) => ({
    time: normalizeTime(b.time),
    open: b.o,
    high: b.h,
    low:  b.l,
    close: b.c,
    color: b.state ? '#2ecc71' : '#e74c3c',
    borderColor: b.state ? '#2ecc71' : '#e74c3c',
    wickColor: b.state ? '#2ecc71' : '#e74c3c',
  }));
  // setData tolerates OHLC on candle series; for area series it will just read `value`
  // Provide a fallback transform for non-candle:
  if (priceSeries.setData.length) {
    try {
      priceSeries.setData(
        (priceSeries.seriesType && priceSeries.seriesType() === 'Area')
          ? candles.map(c => ({ time: c.time, value: c.close }))
          : candles
      );
    } catch {
      // Some builds don’t expose seriesType(); default to close
      priceSeries.setData(candles.map(c => ({ time: c.time, value: c.close })));
    }
  }

  // Small LW markers (only if the series supports setMarkers)
  if (typeof priceSeries.setMarkers === 'function') {
    const markers = [];
    for (const b of bars || []) {
      if (b.upw)
        markers.push({
          time: normalizeTime(b.time),
          position: 'belowBar',
          color: 'green',
          shape: 'text',
          text: '▲',
          size: 2,
        });
      if (b.dnw)
        markers.push({
          time: normalizeTime(b.time),
          position: 'aboveBar',
          color: 'red',
          shape: 'text',
          text: '▼',
          size: 2,
        });
    }
    priceSeries.setMarkers(markers);
  }

  // (HTML overlay removed)

  // Indicator lines (feature-detected creation, reused)
  function ensureLineLikeSeries(cacheKey, color) {
    if (chartApi[cacheKey]) return chartApi[cacheKey];
    let s = null;
    if (typeof chartApi.addLineSeries === 'function') {
      s = chartApi.addLineSeries({ color });
    } else if (typeof chartApi.addAreaSeries === 'function') {
      s = chartApi.addAreaSeries({}); // color not guaranteed here
    } else {
      console.warn('[HACO] No line/area series available for indicators; skipping', cacheKey);
      chartApi[cacheKey] = null;
      return null;
    }
    chartApi[cacheKey] = s;
    return s;
  }

  const zlHaU = ensureLineLikeSeries('__zlHaU', 'blue');
  const zlClU = ensureLineLikeSeries('__zlClU', 'orange');
  const zlHaD = ensureLineLikeSeries('__zlHaD', 'purple');
  const zlClD = ensureLineLikeSeries('__zlClD', 'gray');

  if (zlHaU?.setData) zlHaU.setData((bars || []).map(b => ({ time: normalizeTime(b.time), value: b.ZlHaU })));
  if (zlClU?.setData) zlClU.setData((bars || []).map(b => ({ time: normalizeTime(b.time), value: b.ZlClU })));
  if (zlHaD?.setData) zlHaD.setData((bars || []).map(b => ({ time: normalizeTime(b.time), value: b.ZlHaD })));
  if (zlClD?.setData) zlClD.setData((bars || []).map(b => ({ time: normalizeTime(b.time), value: b.ZlClD })));

  chartApi.timeScale().fitContent();

  // ===== Keep signal chart aligned with main chart =====
  if (typeof window.__getSignalChart === 'function' && window.HACOSync) {
    const sub = window.__getSignalChart();
    if (sub && !chartApi.__linked) {
      HACOSync.linkTimeScales(chartApi, sub);
      chartApi.__linked = true;
    }
  }
}

function explainLast(last) {
  const el = document.getElementById('haco-explain');
  if (!el) return;
  el.innerHTML = `<p>State: ${last?.state ?? ''} (${last?.upw ? 'UP' : ''}${last?.dnw ? 'DOWN' : ''})</p><p>${last?.reasons ?? ''}</p>`;
}

// Optional scan helpers (only run if inputs exist)
async function scan(direction) {
  const input = document.getElementById('haco-scanList');
  if (!input) return;
  const list = input.value.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
  const timeframe = document.getElementById('haco-timeframe').value.trim();
  const results = [];
  for (const sym of list) {
    const url = `/api/signals/haco?symbol=${sym}&timeframe=${timeframe}&lookback=2`;
    try {
      const res = await fetch(url);
      if (!res.ok) continue;
      const data = await res.json();
      if (direction === 'buy' && data.last.upw) results.push({ sym, mark: '✅' });
      else if (direction === 'sell' && data.last.dnw) results.push({ sym, mark: '❌' });
      else results.push({ sym, mark: data.last.state ? '⤴' : '⤵' });
    } catch (_) {}
  }
  const out = results.map((r) => `${r.sym} ${r.mark}`).join('<br>');
  const outEl = document.getElementById('haco-scanResults');
  if (outEl) outEl.innerHTML = out;
}

// Wire up buttons if present
const runBtn = document.getElementById('haco-run');
if (runBtn) runBtn.addEventListener('click', fetchHaco);
const scanBuyBtn = document.getElementById('haco-scanBuy');
if (scanBuyBtn) scanBuyBtn.addEventListener('click', () => scan('buy'));
const scanSellBtn = document.getElementById('haco-scanSell');
if (scanSellBtn) scanSellBtn.addEventListener('click', () => scan('sell'));

// Initial load
fetchHaco();
