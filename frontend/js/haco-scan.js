// /js/haco-scan.js
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('scan-form');
  const input = document.getElementById('scan-symbols');
  const tbody = document.querySelector('#scan-table tbody');
  const statusEl = document.getElementById('scan-status');
  const btn = document.getElementById('scan-run');

  const legendId = 'scan-legend';

  function ensureLegend() {
    // Minimal, no-CSS legend explaining the symbols
    let el = document.getElementById(legendId);
    if (!el) {
      el = document.createElement('div');
      el.id = legendId;
      el.className = 'muted';
      statusEl?.parentNode?.insertBefore(el, statusEl.nextSibling);
    }
    el.textContent = 'Legend: ✅ Up trigger, ❌ Down trigger, ★ Changed on this bar, ' +
                     'UP/DOWN = current HACO state, 1 = true, 0 = false';
  }
  
  async function runTableScan() {
    const list = (input?.value || '')
      .split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
    if (!list.length) { if (statusEl) statusEl.textContent = 'Enter 1+ symbols.'; return; }

    const tfEl = document.getElementById('haco-timeframe');
    const timeframe = tfEl ? tfEl.value.trim() : 'Day';

    if (statusEl) statusEl.textContent = 'Scanning…';
    try {
      const url = `/api/signals/haco/scan?symbols=${encodeURIComponent(list.join(','))}&timeframe=${encodeURIComponent(timeframe)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const rows = await res.json(); // [{symbol, upw, dnw, state, changed, reason}]
      if (tbody) tbody.innerHTML = '';
      for (const r of rows) {
        const tr = document.createElement('tr');
        const upCell = r.upw ? '✅ 1' : '–';
        const dnCell = r.dnw ? '❌ 1' : '–';
        const chCell = r.changed ? '★ 1' : '–';
        tr.innerHTML = `
          <td>${r.symbol}</td>
          <td>${upCell}</td>
          <td>${dnCell}</td>
          <td>${r.state ? 'UP' : 'DOWN'}</td>
          <td>${chCell}</td>
          <td>${r.reason || ''}</td>`;
        tbody?.appendChild(tr);
        if (r.changed) tr.style.background = 'rgba(255,215,0,.12)';
      }
      if (statusEl) statusEl.textContent = `Done • ${rows.length} symbols`;
      ensureLegend();
      document.getElementById('haco-table')?.scrollIntoView({behavior:'smooth', block:'start'});
    } catch (e) {
      console.error('HACO table scan failed', e);
      if (statusEl) statusEl.textContent = 'Scan failed.';
    }
  }

  // Bind BOTH click and submit (redundant safety)
  form?.addEventListener('submit', (e) => { e.preventDefault(); runTableScan(); });
  btn?.addEventListener('click', () => runTableScan());
});
