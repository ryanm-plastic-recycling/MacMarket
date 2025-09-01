document.addEventListener('DOMContentLoaded', () => {
  const $ = (s)=>document.querySelector(s);
  const statusEl = $('#alert-status');
  const tableBody = $('#alerts-table tbody');
  const getUserId = () => {
    const v = localStorage.getItem('userId');
    const n = v ? Number(v) : NaN;
    return Number.isFinite(n) && n>0 ? n : 1; // TODO: replace with real auth context
  };
  const authHeaders = () => ({ 'X-User-Id': String(getUserId()) });

  async function load() {
    status('Loading…');
    const r = await fetch(`/api/alerts?userId=${getUserId()}`, { headers: authHeaders() });
    const rows = r.ok ? await r.json() : [];
    tableBody.innerHTML = '';
    if (!rows.length) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="7" class="muted">No alerts found for user ${getUserId()}.</td>`;
      tableBody.appendChild(tr);
      status('No alerts yet');
      return;
    }
    for (const a of rows) {
      tableBody.appendChild(rowEl(a));
    }
    status(`Loaded ${rows.length} alerts`);
  }

  function rowEl(a){
    const tr = document.createElement('tr');
    tr.dataset.id = a.id;
    tr.innerHTML = `
      <td><input value="${a.symbol}" class="inp-symbol"></td>
      <td>
        <select class="inp-strategy">
          <option ${a.strategy==='HACO'?'selected':''}>HACO</option>
          <option ${a.strategy==='MACD'?'selected':''}>MACD</option>
        </select>
      </td>
      <td>
        <select class="inp-freq">
          ${['5m','15m','1h','1d'].map(f=>`<option ${a.frequency===f?'selected':''}>${f}</option>`).join('')}
        </select>
      </td>
      <td><input value="${a.email||''}" class="inp-email"></td>
      <td><input value="${a.sms||''}" class="inp-sms"></td>
      <td style="text-align:center;"><input type="checkbox" class="inp-enabled" ${a.is_enabled? 'checked':''}></td>
      <td>
        <button class="btn-save">Save</button>
        <button class="btn-tpl">Templates</button>
        <button class="btn-del">Delete</button>
      </td>`;
    tr.querySelector('.btn-save').addEventListener('click', ()=> save(tr));
    tr.querySelector('.btn-del').addEventListener('click', ()=> del(tr));
    tr.querySelector('.btn-tpl').addEventListener('click', ()=> editTpl(tr, a));
    return tr;
  }

  function status(msg){ if(statusEl) statusEl.textContent = msg; }

  async function save(tr){
    const id = tr.dataset.id;
    const payload = {
      symbol: tr.querySelector('.inp-symbol').value.trim().toUpperCase(),
      strategy: tr.querySelector('.inp-strategy').value,
      frequency: tr.querySelector('.inp-freq').value,
      email: tr.querySelector('.inp-email').value.trim() || null,
      sms: tr.querySelector('.inp-sms').value.trim() || null,
      is_enabled: tr.querySelector('.inp-enabled').checked ? 1 : 0
    };
    const r = await fetch(`/api/alerts/${id}`, {method:'PUT', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify(payload)});
    status(r.ok ? 'Saved' : 'Save failed');
  }

  async function del(tr){
    const id = tr.dataset.id;
    if(!confirm('Delete this alert?')) return;
    const r = await fetch(`/api/alerts/${id}`, {method:'DELETE', headers: authHeaders()});
    if(r.ok){ tr.remove(); status('Deleted'); } else { status('Delete failed'); }
  }

  async function create(){
    const payload = {
      user_id: getUserId(),
      symbol: document.getElementById('a-symbol').value.trim().toUpperCase(),
      strategy: document.getElementById('a-strategy').value,
      frequency: document.getElementById('a-freq').value,
      email: document.getElementById('a-email').value.trim() || null,
      sms: document.getElementById('a-sms').value.trim() || null,
      is_enabled: 1
    };
    const r = await fetch('/api/alerts', {method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body: JSON.stringify(payload)});
    if(r.ok){ await load(); status('Created'); } else { status('Create failed'); }
  }

  async function editTpl(tr, a0){
    const id = tr.dataset.id;
    // lightweight “modal”: prompt for email & sms template
    const curEmail = a0.email_template || 'HACO {{symbol}} changed to {{state}} on {{ts}} ({{frequency}}). Reason: {{reason}}';
    const curSms   = a0.sms_template   || '{{symbol}} {{state}} ({{strategy}} {{frequency}}).';
    const email_template = prompt('Email template (use {{symbol}} {{strategy}} {{frequency}} {{state}} {{reason}} {{ts}} {{price}}):', curEmail);
    if(email_template===null) return;
    const sms_template = prompt('SMS template:', curSms);
    if(sms_template===null) return;
    const r = await fetch(`/api/alerts/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email_template, sms_template})});
    status(r.ok ? 'Templates saved' : 'Save failed');
  }

  document.getElementById('a-create')?.addEventListener('click', create);
  load();
});
