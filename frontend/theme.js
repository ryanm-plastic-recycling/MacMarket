const LOGO_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAA8CAIAAAC1nk4lAAABBUlEQVR4nO3ZIY6FMBSF4QumqaEJC0GgkZCyAhQ7YWVdAwaCQqDQCBZAOuIlT047k/RM3uR8Do75QwmGzHsvnyb/64DfYDQKo1EYjcJoFEajMBqF0SiMRmE0CqNRGI3CaJR/Gq21HobhfTmOo9Y6OCUVjlZK7fv+PI+IeO+P41BKBaekol6Puq7neRaRZVmqqoqc0omKttY650TEOWetjZwS8iHGmOu6mqbx3nddd9+3MSY4JRX1pMuyzPP8PE8RKYoickon9pPX9/00TW3b/mhKJXgWrxNf1zXLsm3b3ne+n5LKPH9fYDAahdEojEZhNAqjURiNwmgURqMwGoXRKIxG+cjoLy35hBgqYf+9AAAAAElFTkSuQmCC';
const LOGO_DARK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAA8CAIAAAC1nk4lAAAAxklEQVR4nO3RIY6FMBRG4Z/BI/AoBIYQDGvoytgJihVQgsMjWAhpME0NGfGSZyYZOoI8Medz7am46ZUAAAAAAAAA/OC9H8fxfRyGwXt/mx71dfsihFBVVZqmkpIkKcsyhHCbHnU/tKRt27quk9S27b7vkek5UUNba40xkowx1trI9EnOuTzP13WVNM9zlmXOudv0qKifPo7juq6iKCSd5xmZnhM1tKRpmvq+X5blT+ljXhtvmua6rrqu3ze/JwAAAAAAAPwX35r1fwek0NG2AAAAAElFTkSuQmCC';
const SPINNER_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAAA/klEQVR4nO2YwRKEMAhD2539/19m7ysQAoyiY6624UmL0m4RWZP1uRoA6QWsajzgt8Nk721Wmojskne2ij0oSxlYGjAD9i8GlNqDHXCsTxiwC471Cy0xNvMe+6uJlhtm0IeT5cPhMejlXUAMxygHmfxQZ7cjP88EtN+qWiv6fCsemcGuQo77jP8Xq4B6ursb26OfFveeGZykF7CqF7AqFVDvMEqdu6Kjnxb3nhm01ZXFuI8JaDeSVUh9vhUvucRZSH6eC+i342wwe7wXB2YQQyJQfww6k4TPxd2nurVi5+PwHqxeYWT9qCLpgmR8nnc3o5pMvN06S0/7F5+v8YA/VapzM2mEhOYAAAAASUVORK5CYII=';
const SPINNER_DARK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAYAAACM/rhtAAABC0lEQVR4nO2YSw7DIAxEoeope8Bek6yQqmKPv2mcilnH4xc7YEIfY7TKelwNIGkDRlUe8Jnkg1ZajxhHALXL//M5M6wHMLIvzVg1qPUbzNo01T4WwOwdXeWnbTE2e4OOvWDoaEK7u2LU8Q8gsG9hUNZIanEOnPw8m8e3UVvhAnEIkH4rL5wcT+azVTAK5/ApP4s5wLXcWdXDfkve21awjDZgVBswKg5w3QPwsLeL9lvy3raCtLKqaPBBgPToiELy8WQ+X4u9kI44CZAfwNZkzhO15sjf2nn/JK0l/JNMnXFPJx6RLN9g8nlL52ddJFmQah/P1cc097T8J3czVLKSt1tpEEh/NosvUHnAAy94PE+UQOHAAAAAAElFTkSuQmCC';

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
