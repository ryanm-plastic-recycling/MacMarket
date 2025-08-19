window.HACO = window.HACO || {};

function showToast(msg, ms = 1500) {
  const t = document.getElementById('haco-toast');
  if (!t) return;
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(showToast._tmr);
  showToast._tmr = setTimeout(() => (t.style.display = 'none'), ms);
}

function bindHacoUI() {
  console.log('[HACO:UI] bind start');
  const form   = document.getElementById('haco-form');
  const input  = document.getElementById('haco-symbol');
  const button = document.getElementById('haco-run');
  console.log('[HACO:UI] found', { form: !!form, input: !!input, button: !!button });

  // Delegated click so re-renders won’t break it
  document.addEventListener('click', (e) => {
    const btn = e.target.closest?.('#haco-run');
    if (!btn) return;
    e.preventDefault();
    const sym = (document.getElementById('haco-symbol')?.value || '').trim().toUpperCase();
    console.log('[HACO:UI] Run (click)', sym);
    if (!sym) return showToast('Enter a symbol (e.g., AAPL)');
    runHaco(sym);
  });

  // Form submit (Enter key)
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const sym = (document.getElementById('haco-symbol')?.value || '').trim().toUpperCase();
    console.log('[HACO:UI] Run (submit)', sym);
    if (!sym) return showToast('Enter a symbol (e.g., AAPL)');
    runHaco(sym);
  });

  console.log('[HACO:UI] bind OK');
}

async function runHaco(symbol) {
  try {
    showToast('Running…');
    if (!window.HACO?.runScan) throw new Error('runScan missing');
    await window.HACO.runScan(symbol);
    showToast('Done');
  } catch (err) {
    console.error('[HACO:UI] run error', err);
    showToast('Scan failed (see console)');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bindHacoUI);
} else {
  bindHacoUI();
}
window.addEventListener('load', () => console.log('[HACO:UI] window load fired'));

