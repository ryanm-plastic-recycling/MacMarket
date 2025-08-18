(async function() {
  const $ = sel => document.querySelector(sel);
  const emailEl = $('#alert-email');
  const smsEl = $('#alert-sms');
  const freqEl = $('#alert-frequency');
  const symIn = $('#symbol-input');
  const symAdd = $('#add-symbol');
  const symList = $('#symbol-list');
  const saveBtn = $('#save-alerts');
  const testBtn = $('#test-alerts');
  const toast = $('#toast');

  let symbols = [];

  function showToast(msg, ok=true) {
    toast.textContent = msg;
    toast.style.display = 'block';
    toast.style.background = ok ? '#e6ffed' : '#ffe6e6';
    setTimeout(() => { toast.style.display = 'none'; }, 2500);
  }

  function renderSymbols() {
    symList.innerHTML = '';
    symbols.forEach((s, i) => {
      const li = document.createElement('li');
      li.textContent = s;
      const btn = document.createElement('button');
      btn.textContent = 'Remove';
      btn.onclick = () => { symbols.splice(i,1); renderSymbols(); };
      li.appendChild(btn);
      symList.appendChild(li);
    });
  }

  symAdd.onclick = () => {
    const v = (symIn.value || '').trim().toUpperCase();
    if (v && !symbols.includes(v)) symbols.push(v);
    symIn.value = '';
    renderSymbols();
  };

  saveBtn.onclick = async () => {
    try {
      const res = await fetch('/api/alerts/me', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: emailEl.value || '',
          sms: smsEl.value || '',
          frequency: freqEl.value,
          symbols
        })
      });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || 'Failed');
      showToast('Saved');
    } catch (e) {
      showToast(e.message, false);
    }
  };

  testBtn.onclick = async () => {
    try {
      const res = await fetch('/api/alerts/test', { method: 'POST' });
      const j = await res.json();
      if (!res.ok || !j.ok) throw new Error('Test failed');
      showToast('Test OK');
    } catch (e) {
      showToast(e.message, false);
    }
  };

  // Load existing settings
  try {
    const res = await fetch('/api/alerts/me');
    if (res.ok) {
      const j = await res.json();
      emailEl.value = j.email || '';
      smsEl.value = j.sms || '';
      freqEl.value = j.frequency || '15m';
      symbols = Array.isArray(j.symbols) ? j.symbols : [];
      renderSymbols();
    }
  } catch {}
})();
