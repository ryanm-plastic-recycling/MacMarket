window.HACO = window.HACO || {};
window.HACO.runScan = async function runScan(symbol) {
  console.log('[HACO] runScan', symbol);
  // Try POST first
  let res = await fetch('/api/signals/haco/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol })
  }).catch(() => null);
  // Fallback to GET if POST not supported
  if (!res || res.status === 404 || res.status === 405) {
    res = await fetch(`/api/signals/haco/scan?symbol=${encodeURIComponent(symbol)}`);
  }
  if (!res || !res.ok) throw new Error(`scan failed: ${res?.status}`);
  const data = await res.json(); // { candles:[{time,open,high,low,close}], markers:[...] }

  const el = document.getElementById('haco-chart');
  if (!el) { console.warn('[HACO] #haco-chart missing'); return; }
  el.innerHTML = '';

  const chart = LightweightCharts.createChart(el, { height: el.clientHeight || 420 });
  const series = chart.addCandlestickSeries();
  if (Array.isArray(data.candles)) series.setData(data.candles);
  if (Array.isArray(data.markers) && data.markers.length) {
    series.setMarkers(data.markers);
  }
  console.log('[HACO] chart rendered');
};
