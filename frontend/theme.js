
const LOGO_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABQklEQVR42u2a2w6DIBBEofG/G78cnzTEKDdh2Rl2n3xqcs4MrG3qQwhu5fm5xccEmIDFxu8++N1fF9+2Evj5HP7B0wuIgeOJ4WmPwB...';
const LOGO_DARK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABQklEQVR42u2a2w6DIBBEofG/G78cnzTEKDdh2Rl2n3xqcs4MrG3qQwhu5fm5xccEmIDFxu8++N1fF9+2Evj5HP7B0wuIgeOJ4WmPwB...';
const SPINNER_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABQklEQVR42u2a2w6DIBBEofG/G78cnzTEKDdh2Rl2n3xqcs4MrG3qQwhu5fm5xccEmIDFxu8++N1fF9+2Evj5HP7B0wuIgeOJ4WmPwB...';
const SPINNER_DARK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABQklEQVR42u2a2w6DIBBEofG/G78cnzTEKDdh2Rl2n3xqcs4MrG3qQwhu5fm5xccEmIDFxu8++N1fF9+2Evj5HP7B0wuIgeOJ4WmPwB...';

function updateThemeAssets(theme) {
  const logo = document.getElementById('header-logo');
  if (logo) {
    logo.src = theme === 'dark' ? LOGO_DARK : LOGO_LIGHT;
  }
  const spinImg = document.getElementById('spinner-image');
  if (spinImg) {
    spinImg.src = theme === 'dark' ? SPINNER_DARK : SPINNER_LIGHT;
  }
}

function applyTheme(theme) {
  document.documentElement.classList.remove('light', 'dark');
  document.documentElement.classList.add(theme);
  localStorage.setItem('theme', theme);
  updateThemeAssets(theme);
}

function initTheme() {
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('theme') || 'light';
  applyTheme(saved);
  const select = document.getElementById('theme-select');
  if (select) {
    select.value = saved;
    select.addEventListener('change', () => applyTheme(select.value));
  }
  if (btn) {
    btn.textContent = saved === 'dark' ? 'Light Mode' : 'Dark Mode';
    btn.addEventListener('click', () => {
      const current = localStorage.getItem('theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      applyTheme(next);
      btn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
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
  spinner.innerHTML = `<img id="spinner-image" class="spin" src="${SPINNER_LIGHT}" alt="loading">`;
  document.body.appendChild(spinner);
  updateThemeAssets(localStorage.getItem('theme') || 'light');
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
