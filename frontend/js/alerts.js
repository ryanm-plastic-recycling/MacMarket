(async function() {
  const $ = sel => document.querySelector(sel);
  const stratEl = $('#alert-strategy');
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
      const card = document.createElement('div');
      card.className = 'card row';
      const title = document.createElement('strong');
      title.textContent = s;
      card.appendChild(title);
      const meta = document.createElement('span');
      meta.textContent = '...';
      card.appendChild(meta);
      const btn = document.createElement('button');
      btn.textContent = 'Remove';
      btn.onclick = () => { symbols.splice(i,1); renderSymbols(); };
      card.appendChild(btn);
      symList.appendChild(card);
      fetch(`/api/quote/${s}`).then(r => r.json()).then(q => {
        const parts = [];
        if (q.name) parts.push(q.name);
        if (q.price !== undefined && q.price !== null) parts.push(q.price);
        meta.textContent = parts.join(' – ');
      }).catch(() => { meta.textContent = ''; });
    });
  }

  symAdd.onclick = () => {
    const v = (symIn.value || '').trim().toUpperCase();
    if (v && !symbols.includes(v)) {
      symbols.push(v);
      renderSymbols();
    }
    symIn.value = '';
  };

  saveBtn.onclick = async () => {
    try {
      const res = await fetch('/api/alerts/me', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy: stratEl.value,
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
      stratEl.value = j.strategy || 'HACO';
      emailEl.value = j.email || '';
      smsEl.value = j.sms || '';
      freqEl.value = j.frequency || '15m';
      symbols = Array.isArray(j.symbols) ? j.symbols : [];
      renderSymbols();
    }
  } catch {}
})();
