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
});
