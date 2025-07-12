function applyTheme(theme) {
  document.documentElement.classList.remove('light', 'dark');
  document.documentElement.classList.add(theme);
  localStorage.setItem('theme', theme);
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  applyTheme(saved);
  const select = document.getElementById('theme-select');
  if (select) select.value = saved;
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const select = document.getElementById('theme-select');
  if (select) {
    select.addEventListener('change', () => applyTheme(select.value));
  }
  initAuth();
  initHeader();
  initLoading();
  if (window.initTickerBar) {
    initTickerBar();
  }
});

function initAuth() {
  const link = document.getElementById('logout-link');
  if (!link) return;
  if (localStorage.getItem('userId')) {
    link.style.display = 'block';
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      await fetch('/api/logout', { method: 'POST' });
      localStorage.removeItem('userId');
      localStorage.removeItem('username');
      localStorage.removeItem('isAdmin');
      window.location.href = 'login.html';
    });
  } else {
    link.style.display = 'none';
  }
}

function initHeader() {
  const info = document.getElementById('user-info');
  const timeDiv = document.getElementById('time');
  if (timeDiv) {
    const update = () => {
      const now = new Date();
      timeDiv.textContent = now.toLocaleString();
    };
    update();
    setInterval(update, 1000);
  }
  if (info) {
    const user = localStorage.getItem('username');
    info.textContent = user ? `Logged in as ${user}` : '';
  }
}

function setStatus(message, type = '') {
  const div = document.getElementById('status');
  if (!div) return;
  if (message) {
    div.textContent = message;
    div.className = type;
    div.style.display = 'block';
  } else {
    div.textContent = '';
    div.className = '';
    div.style.display = 'none';
  }
}

window.setStatus = setStatus;

function initLoading() {
  const spinner = document.createElement('div');
  spinner.id = 'loading-spinner';
  spinner.innerHTML = '<div class="spin"></div>';
  document.body.appendChild(spinner);
  let count = 0;
  const origFetch = window.fetch;
  window.fetch = async (...args) => {
    count++;
    spinner.style.display = 'block';
    try {
      return await origFetch(...args);
    } finally {
      count--;
      if (count <= 0) {
        spinner.style.display = 'none';
        count = 0;
      }
    }
  };
}
