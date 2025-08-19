// HACO UI binding with delegation + diagnostics
window.HACO = window.HACO || {};

function showToast(msg, ms = 1800) {
  const t = document.getElementById('haco-toast');
  if (!t) return;
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(showToast._tmr);
  showToast._tmr = setTimeout(() => (t.style.display = 'none'), ms);
}

function bindHacoUI() {
  console.log('[HACO:UI] bind start, readyState=', document.readyState);
  const form   = document.getElementById('haco-form');
  const button = document.getElementById('get-signal');
  const input  = document.getElementById('symbol');
  console.log('[HACO:UI] elements found', { form: !!form, button: !!button, input: !!input });

  // Delegated handler works even if elements are re-rendered later.
  document.addEventListener('click', (e) => {
    const target = e.target.closest?.('#get-signal');
    if (!target) return;
    e.preventDefault();
    const sym = (document.getElementById('symbol')?.value || '').trim().toUpperCase();
    console.log('[HACO:UI] Run (click) symbol=', sym);
    if (!sym) return showToast('Enter a symbol (e.g., AAPL)');
    runHaco(sym);
  });

  // Form submit (Enter key)
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const sym = (document.getElementById('symbol')?.value || '').trim().toUpperCase();
    console.log('[HACO:UI] Run (submit) symbol=', sym);
    if (!sym) return showToast('Enter a symbol (e.g., AAPL)');
    runHaco(sym);
  });

  // Quick hint when input changes
  input?.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') return; // submit handler will catch it
    console.log('[HACO:UI] input=', e.target.value);
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
  // Already parsed
  bindHacoUI();
}
window.addEventListener('load', () => console.log('[HACO:UI] window load fired'));
