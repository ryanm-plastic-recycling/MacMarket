// HACO scan client – tries POST, falls back to GET, renders chart
window.HACO = window.HACO || {};
window.HACO.runScan = async function runScan(symbol) {
  console.log('[HACO:SCAN] start', { symbol });
  let res;
  try {
    res = await fetch('/api/signals/haco/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
    console.log('[HACO:SCAN] POST status', res.status);
    if (res.status === 404 || res.status === 405) throw new Error('fallback');
  } catch {
    const url = `/api/signals/haco/scan?symbol=${encodeURIComponent(symbol)}`;
    console.log('[HACO:SCAN] fallback GET', url);
    res = await fetch(url);
  }
  if (!res.ok) throw new Error(`scan failed: ${res.status}`);
  const data = await res.json();
  console.log('[HACO:SCAN] payload', data);

  const el = document.getElementById('haco-chart');
  if (!el) { console.warn('[HACO:SCAN] #haco-chart missing'); return; }
  el.innerHTML = '';

  if (!window.LightweightCharts) {
    throw new Error('LightweightCharts not loaded');
  }
  const chart = LightweightCharts.createChart(el, { height: el.clientHeight || 420 });
  const series = chart.addCandlestickSeries();
  if (Array.isArray(data.candles)) series.setData(data.candles);
  if (Array.isArray(data.markers) && data.markers.length) series.setMarkers(data.markers);
  console.log('[HACO:SCAN] chart rendered');
};
