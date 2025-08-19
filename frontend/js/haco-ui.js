window.HACO = window.HACO || {};
document.addEventListener('DOMContentLoaded', () => {
  console.log('[HACO] UI init');
  const runBtn = document.getElementById('get-signal');
  const symbol = document.getElementById('symbol');
  if (!runBtn || !symbol) {
    console.warn('[HACO] Missing #get-signal or #symbol; UI not bound.');
    return;
  }
  runBtn.onclick = async () => {
    const sym = (symbol.value || '').trim().toUpperCase();
    if (!sym) { alert('Enter a symbol (e.g., AAPL)'); return; }
    try {
      await (window.HACO.runScan ? window.HACO.runScan(sym) : Promise.reject('runScan missing'));
    } catch (e) {
      console.error('[HACO] run error', e);
      alert('Scan failed. Check console for details.');
    }
  };
});
