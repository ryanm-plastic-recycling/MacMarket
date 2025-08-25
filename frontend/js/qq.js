// QuiverQuant frontend helpers

function setStatus(msg) {
    const el = document.getElementById('status');
    if (el) el.textContent = msg;
}

async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error('Request failed');
    return res.json();
}

async function loadStrategies() {
    const data = await fetchJSON('/api/qq/strategies');
    const select = document.getElementById('strategySelect');
    select.innerHTML = '';
    data.data.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
    });
}

async function syncLatest() {
    setStatus('Syncing...');
    await fetchJSON('/api/qq/ingest/latest', {method: 'POST'});
    setStatus('Done');
    await loadStrategies();
}

async function runRebalances() {
    setStatus('Running...');
    await fetchJSON('/api/qq/run-rebalances', {method: 'POST'});
    setStatus('Completed');
}

async function init() {
    await loadStrategies();
    document.getElementById('syncBtn').onclick = syncLatest;
    document.getElementById('runBtn').onclick = runRebalances;
}

document.addEventListener('DOMContentLoaded', init);
