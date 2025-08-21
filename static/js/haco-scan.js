document.addEventListener('DOMContentLoaded', () => {
  const form   = document.getElementById('scan-form');
  const input  = document.getElementById('scan-symbols');
  const status = document.getElementById('scan-status');
  const tbody  = document.querySelector('#scan-table tbody');
  if (!form || !input || !tbody) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const syms = (input.value || '').toUpperCase().split(',').map(s => s.trim()).filter(Boolean);
    if (!syms.length) { status.textContent = 'Enter at least one symbol.'; return; }

    status.textContent = 'Scanning…';
    tbody.innerHTML = '';
    try {
      const url = '/api/signals/haco/scan?symbols=' + encodeURIComponent(syms.join(','));
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const rows = await res.json();
      for (const r of rows) {
        const tr = document.createElement('tr');
        if (r.error) {
          tr.innerHTML = `<td>${r.symbol}</td><td colspan="5" style="color:#b00;">${r.error}</td>`;
        } else {
          const arrow = (v, up) => v ? (up ? '▲' : '▼') : '—';
          tr.innerHTML = `
            <td>${r.symbol}</td>
            <td style="color:#2ecc71;">${arrow(r.upw, true)}</td>
            <td style="color:#e74c3c;">${arrow(r.dnw, false)}</td>
            <td>${r.state ?? '—'}</td>
            <td>${r.changed ? 'Yes' : 'No'}</td>
            <td style="max-width:520px;overflow-wrap:anywhere;">${r.reason || '—'}</td>`;
        }
        tbody.appendChild(tr);
      }
      status.textContent = `Scan complete (${rows.length} symbols).`;
    } catch (err) {
      status.textContent = 'Scan failed: ' + (err?.message || err);
    }
  });

  // Optional: auto-run once on load
  // form.dispatchEvent(new Event('submit'));
});
