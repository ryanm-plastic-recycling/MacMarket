  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = saved === 'dark' ? 'Light Mode' : 'Dark Mode';
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.addEventListener('click', () => {
      const current = localStorage.getItem('theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      applyTheme(next);
      btn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
    });
