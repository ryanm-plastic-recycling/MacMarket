(function () {
  const table = document.getElementById('journal-table');
  const tbody = document.getElementById('journal-tbody');
  if (!table || !tbody) return; // graceful no-op if IDs missing

  function norm(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .replace(/[^\w %$]/g, '') // strip punctuation
      .trim();
  }

  function findColIndexes() {
    // Build a normalized header map: text -> index
    const map = {};
    const ths = table.querySelectorAll('thead th, thead td');
    ths.forEach((th, i) => {
      const key = norm(th.textContent || th.innerText);
      if (key) map[key] = i;
    });
    const qtyIdx = firstIdx(map, ['qty', 'quantity', 'shares']);
    const priceIdx = firstIdx(map, ['price', 'buy price', 'entry', 'entry price']);
    const currentIdx = firstIdx(map, ['current', 'last', 'current price', 'mark', 'last price']);
    if ([qtyIdx, priceIdx, currentIdx].some(i => i == null)) return null;
    return { qtyIdx, priceIdx, currentIdx };
  }

  function firstIdx(map, keys) {
    for (const k of keys) if (k in map) return map[k];
    return null;
  }

  function toNum(x) {
    if (x == null) return 0;
    // strip $, commas, %, spaces; handle parentheses negatives
    const s = String(x)
      .replace(/[,$%\s]/g, '')
      .replace(/^\((.*)\)$/, '-$1');
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtUSD(n) {
    return n.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function fmtPct(n) {
    return `${(n * 100).toFixed(1)}%`;
  }

  function compute() {
    const idx = findColIndexes();
    if (!idx) return;

    let invested = 0;
    let current = 0;

    tbody.querySelectorAll('tr').forEach(tr => {
      const tds = tr.querySelectorAll('td');
      if (tds.length === 0) return;
      const qty = toNum(tds[idx.qtyIdx]?.textContent);
      const price = toNum(tds[idx.priceIdx]?.textContent);
      const cur = toNum(tds[idx.currentIdx]?.textContent);
      invested += qty * price;
      current += qty * cur;
    });

    const profit = current - invested;
    const pct = invested > 0 ? current / invested - 1 : null;

    const elInvested = document.getElementById('total-invested');
    const elCurrent = document.getElementById('current-positions');
    const elProfit = document.getElementById('total-profit');
    const elPct = document.getElementById('percent-return');
    if (elInvested) elInvested.textContent = fmtUSD(invested);
    if (elCurrent) elCurrent.textContent = fmtUSD(current);
    if (elProfit) {
      elProfit.textContent = fmtUSD(profit);
      elProfit.classList.toggle('neg', profit < 0);
      elProfit.classList.toggle('pos', profit >= 0);
    }
    if (elPct) {
      if (pct == null) {
        elPct.textContent = '—';
        elPct.classList.remove('neg', 'pos');
      } else {
        elPct.textContent = fmtPct(pct);
        elPct.classList.toggle('neg', pct < 0);
        elPct.classList.toggle('pos', pct >= 0);
      }
    }
  }

  // Run at load
  document.addEventListener('DOMContentLoaded', compute);
  // Run whenever tbody changes (rows appended/edited)
  const mo = new MutationObserver(() => compute());
  mo.observe(tbody, { childList: true, subtree: true, characterData: true });
  // Expose manual hook for async renderers
  window.recomputeJournalTotals = compute;
})();

