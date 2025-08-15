// /static/js/haco-ui.js
(function () {
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
        updateMarkers(next) {
          data = Array.isArray(next) ? next : data;
          redraw();
        },
        redraw,
      };
    }

    return { attach };
  })();

  window.HACOOverlay = HACOOverlay;
})();

// ===== Signal sub-chart: create once if the element exists =====
(function () {
  const signalChartEl = document.getElementById('haco-signal-chart');
  if (!signalChartEl) return;

  const LW = window.LightweightCharts;
  if (!LW || typeof LW.createChart !== 'function') return;

  if (!signalChartEl.__signalChart) {
    signalChartEl.textContent = '';
    signalChartEl.__signalChart = LW.createChart(signalChartEl, {
      height: 100,
      timeScale: { visible: false },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: false },
    });
    signalChartEl.__signalSeries = signalChartEl.__signalChart.addHistogramSeries({
      priceScaleId: '',
      priceFormat: { type: 'price', precision: 0, minMove: 1 },
    });
    signalChartEl.__signalSeries.priceScale().applyOptions({
      scaleMargins: { top: 0, bottom: 0 },
    });
  }

  // Setter used by renderChart()
  window.__setSignalData = (bars) => {
    const series = signalChartEl.__signalSeries;
    if (!series) return;
    const data = (bars || []).map((b) => ({
      time: b.time,
      value: 1,
      color: b.state ? '#2ecc71' : '#e74c3c',
    }));
    series.setData(data);
    signalChartEl.__signalChart.timeScale().fitContent();
  };
})();

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
  renderChart(data.series);
  explainLast(data.last);
}

function renderChart(bars) {
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

    const price = api.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    Object.defineProperties(chartEl, {
      __hacoChart: { value: api, writable: false },
      __hacoPrice: { value: price, writable: false },
    });
  }

  const chartApi = chartEl.__hacoChart;
  const priceSeries = chartEl.__hacoPrice;

  if (!chartApi || typeof chartApi.addCandlestickSeries !== 'function') {
    console.error('[HACO] Unexpected chart object:', chartApi);
    return;
  }
  if (!priceSeries || typeof priceSeries.setData !== 'function') {
    console.error('[HACO] Unexpected price series object:', priceSeries);
    return;
  }

  // Update sub-chart (if present)
  if (typeof window.__setSignalData === 'function') {
    window.__setSignalData(bars);
  }

  // Candles
  const candles = (bars || []).map((b) => {
    const up = '#2ecc71',
      down = '#e74c3c';
    const col = b.state ? up : down;
    return {
      time: b.time,
      open: b.o,
      high: b.h,
      low: b.l,
      close: b.c,
      color: col,
      borderColor: col,
      wickColor: col,
    };
  });
  priceSeries.setData(candles);

  // Small LW markers
  const markers = [];
  for (const b of bars || []) {
    if (b.upw)
      markers.push({
        time: b.time,
        position: 'belowBar',
        color: 'green',
        shape: 'text',
        text: '▲',
        size: 2,
      });
    if (b.dnw)
      markers.push({
        time: b.time,
        position: 'aboveBar',
        color: 'red',
        shape: 'text',
        text: '▼',
        size: 2,
      });
  }
  priceSeries.setMarkers(markers);

  // Big HTML arrows overlay (non-blocking)
  if (window.HACOOverlay && typeof window.HACOOverlay.attach === 'function') {
    window.HACOOverlay.attach({ container: chartEl, chart: chartApi, series: priceSeries, bars });
  }

  // Indicator lines (reuse if they already exist)
  const zlHaU = chartApi.__zlHaU || chartApi.addLineSeries({ color: 'blue' });
  const zlClU = chartApi.__zlClU || chartApi.addLineSeries({ color: 'orange' });
  const zlHaD = chartApi.__zlHaD || chartApi.addLineSeries({ color: 'purple' });
  const zlClD = chartApi.__zlClD || chartApi.addLineSeries({ color: 'gray' });
  chartApi.__zlHaU = zlHaU;
  chartApi.__zlClU = zlClU;
  chartApi.__zlHaD = zlHaD;
  chartApi.__zlClD = zlClD;

  zlHaU.setData(bars.map((b) => ({ time: b.time, value: b.ZlHaU })));
  zlClU.setData(bars.map((b) => ({ time: b.time, value: b.ZlClU })));
  zlHaD.setData(bars.map((b) => ({ time: b.time, value: b.ZlHaD })));
  zlClD.setData(bars.map((b) => ({ time: b.time, value: b.ZlClD })));

  // Optional Heikin-Ashi overlay
  if (document.getElementById('haco-toggleHa')?.checked) {
    if (!chartApi.__haSeries) {
      chartApi.__haSeries = chartApi.addCandlestickSeries({ upColor: '#999', downColor: '#555' });
    }
    chartApi.__haSeries.setData(
      bars.map((b) => ({
        time: b.time,
        open: b.haOpen,
        high: Math.max(b.h, b.haOpen, b.haC),
        low: Math.min(b.l, b.haOpen, b.haC),
        close: b.haC,
      }))
    );
  }

  chartApi.timeScale().fitContent();
}

function explainLast(last) {
  const el = document.getElementById('haco-explain');
  el.innerHTML = `<p>State: ${last.state} (${last.upw ? 'UP' : ''}${last.dnw ? 'DOWN' : ''})</p><p>${last.reasons}</p>`;
}

// Optional scan helpers (only run if buttons/inputs exist in DOM)
async function scan(direction) {
  const input = document.getElementById('haco-scanList');
  if (!input) return; // avoid errors if element not present
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
