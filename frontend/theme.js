// Embed assets directly to avoid additional network requests that were
// causing 404 errors when the module files were not served.
const LOGO_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAADAElEQVR4nO3ZvWsUQRjH8a+JBKKNL4UBJWJvQNRGbMReSwlEKxXRgP4tRsEXEBUEUbSysLPUJo1oISiIhZIiCCqCLzGxOAm3uZu9vc3u7I33/UCK5Jm5+RGe3duZBUmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJElpuA6sFPxZAibXsdZ0H2ut/Bv/v+evxEikdUaBC+uYf7GqICWlnj8oVgMAnAXGS8w7CByqOEsZqefvKmYDbANmSsy7VHWQklLP31XMBoD+b4UTwIk6gpSUev4OsRtgCjjSx/jzwFg9UUpJPX+H2A0Axa+iMeBcnUFKSj1/RhMNcBzYXWDcNLCj5ixlpJ4/o4kGGAVmC4wb1K1T6vkz6myA38BioHYG2JQz9zBwIFD7tJ5QfUg9fyF1NsAycDNQ2wqczJmbt3W6VjpRf1LPX7teR6k/gJ20rqRu9VeBz92VM+cdsL/HulUdBQ96/krU/QzwEXgcqO0Fjnb5+yywMTDnCq0rM5bU8/cU4yFwLqe29kFpnNaRazffgNuVJOpP6vlzxWiA58B8oHYM2NP2+wywPTD2DvC1uliFpZ4/V6xtYOgqGiG7pQptnVZo3T6bknr+oFgN8ABYCNROA5tpfZ9OBcY8Bd7WkKuo1PMHxWqAX8CNQG0LcIr8g5O87+EYUs9fiyLbqHYTwM/A2A/An0DtDbCh7XP29Vi3ym3gIOevRMyj4AXgYaA2mZNljtY/pWmp5+8q9ruAy32O/wLcrSNISann7xC7AeaBF32MvwV8rylLGann79DE28CiD0TLwNU6g5SUev6MJhrgEa0j1l6eAO9rzlJG6vkzmmiAJYq9ERvUrVPq+TOaaABo7anXbrPavQaeRcpSRur5VzXVAIvA/Zz6oF89qedf1VQDQHhL9Rm4FzNISannB8LvrWN4SfaELDWp5weavQNoANgAQ84GGHI2wJCzAYacDSBJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJUrP+AnUmH7yWWX8KAAAAAElFTkSuQmCC';
const LOGO_DARK = 'data:image/png;base64,' +
  'iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAADHklEQVR4nO3Zv2sUQRjG8ec1ElAbfxRaSMTeVNqIjd' +
  'hHsJFAtNIgGtTaP8MoGgVRQRBFK0HBwlKbNIKNiFhFUgRBRZAY8lokStbcbHb3bmZvvO+nS94Z9ime3bu5lQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABkwN1nvLoldx/p4lrjNa7l7j7+v+fvlU2JrjMk6UIX+y/1KkhDuecPSlUASZp09y11N7n7IUmHI+SpK/f8HaUswE5JEw32Xe51kIZyz99RygJINR+F7r5H0slIWZrIPf86qQsw6u5Ha6w/L2k4UpYmcs+/TuoCSBXvIncflnQucpYmcs9f0EYBjrv7vgrrxiXtjh2mgdzzF7RRgCFJUxXW9evRKff8BTEL8EvSQmB21t23hja6+xFJBwPjz90Gqyj3/JXELMCypNuB2Q5Jp0r2lh2dbjZOVE/u+SuJ/RFwQ9JSYHax0z/dfa+kE4E9HyU970GuqnLPv6GoBTCzOUlPA+MD7n6sw/+nJG0O7LmmlTszidzzV5HiS+B0yazwRWn1p9bJwNrvku72KlQNuecvFb0AZvZa0mxgPObu+9f8PSFpV2DtPTP71tNwFeSefyOpjoGhu2iTikeq0NHJtfL4bEvu+YNSFeCRpPnA7Iy7b1v9PB0NrHlhZh/iRKsk9/xBSQpgZouSbgXG2yWdVvkPJ2Wfw9Hlnr9Myl8CZyQtBmZXJI0FZu8lvYySqJ7c83eUrABmNi/pcWA8UpJl2sw8Tqrqcs8fkvpdwNWa679Kuh8jSEO5518naQHMbFbSmxpb7pjZj1h56so9fydtvA2s+oVoWdL1mEEayj1/QRsFeCJprsK6Z2b2KXaYBnLPX5C8AGa2pGpvxPry6JR7/n+18QSQVs7UP0vm78zsVaowDeSe/69WCmBmC5Ielizp67sn9/xrtfUEkMJHqi+SHqQM0lDu+SWF31tHZ2ZvJVlb1+9W7vn/aPMJgD5AAQYcBRhwFGDAUYABRwEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGjXb/T0o7AK1Og7AAAAAElFTkSuQmCC';
const SPINNER_LIGHT = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAC80lEQVR4nO3d0VLrUAiFYXR8/1fWK8c2pk2asmEB/3d/RjaskNjTWjMAAAAAAAAAAAAAANDNR3YBgb4v/Jv2/el6wCvDPqtVz7ocZuXAj5TuYeniLXfwWyV7WbFopaE/UqavZQq1GoPfku+vfIFWc/Bbsn3+zC7gAMNf7Cu7gAc6DL4ExQ3QafjSV7+ZXgA6Db8ElYR2HLxKb59SeAaIGv6VgXQM5p3slFZ7zf5svdl9PS2z0BXDjzzPo/rLDN8sr1jv4SsFmQAc8By+UrO/TaueU6IL9hp+uUarUnsd4AyG70jhoeksBr9A1AZg+KIiAsDwhak/AzD8xVYH4J2rn+EHWBkAhl+A4i2A4QdaFYCrVz/DD6a4ARBoRQC4+gtR2QAMP4lKAJDEOwB8BLsYNsBwngHg6i+IDTBcZgC4+gWwAYbzCkD7D1B0lbUBWP8iuAUMRwCGIwDDeQTg1QdA7v9C2ADDEYDhCMBwBGA4AjCcwt8Iwn9hv1mxAYYjAMMRgOEIwHAEYDgCMJxHAF79FYR3Dz0X+p9rbIDhCMBwBGC4rADwHLAvvC9eAeBdPjne7ju3gOEyA8Bt4F5KP9gAw3kGgO/kuS7to/VsgOG8A8AWeF3qH9ZgAwynEoCpWyD93CsCcHU9pTcjmMQf1FTZAEiyKgBsgeckrn4zzQ3QPRRS51sZgHfSKtUkR3JforF6AxCCP3LDN9O8BdzqEgLZc0QE4N30yjbvJOmvzYvaAFNDID38kB+w4THICu8+KnNO9WeAPerbQL2+OxlXk2eDlLZByXNlNdD7KskMQumzdGqcWex5qtef8wM3Vt4vV5ytWr2aP3Qj6qFJ+d1KaXNQCIBZsSdnZ6kzUAnAr0lBkOi92usAEk0JIHNOtQCYCTVnEanzSRWzo9MtQbLXihvglmTTLpA9h2xhOypuA/n+yhe4o0IQyvS1TKEPKIWhZC9LFr0jMwile1i6+CfavWa/SqvDHODr7QEAAAAAAAAAAAAAU/wA5ZRWqlitYM8AAAAASUVORK5CYII=';
const SPINNER_DARK = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAADB0lEQVR4nO3d23biMAyFYTFr3v+VM1fpUBdoDpa0Zf3ffReyta0EysEMAAAAAAAAAAAAAACs5pFdQJRt27azf/N4PJbfnyUXeKXZR60WiiUW49nw31QPROniMxs/qhqEckUrNf2dSmEoU2iFxo8qBEG+wIqNHykH4U92AZ/QfH9/swt4ZYXGVyE3AVZqvvrpNxMLwErNr0IioSs2vsLpNxO4B4hq/pWGrBjMUWpKq71mf7TeKqffLDEAHs2P3Ph39VdqvllSAGY3P3PTx7UQgF/MbL7SZm/btinVc1RowbOaX3GjVUm9DnAEzZ8r/abpKBrvI2QC0Hxd7gGg+dqk7wFovj/XANw5/TQ/hlsAaH4NcpcAmh/LJQBXTz/Njyc3ARBregA4/bVITACan0ciAMgzNQB8BLseJkBz0wLA6a+JCdBcWgA4/RqYAM1NCUCHD1CsKmUCMP51cAlojgA0RwCaux2AszeAXP+1MAGaIwDNEYDmCEBzBKC59O8Iwk+Rz6yYAM0RgOYIQHMEoDkC0BwBaO52AM4+BeHdQ59F/3ONCdAcAWiOADSXEgDuA17L2JcpAeBdPjlm7DuXgObSAsBl4Lus/WACNDctAPwmz3WZH61nAjQ3NQBMgfOyv1iDCdCcRAC6TgGFdU8PwNXxpLAZkVS+UFNiAiCPSwCYAp+pnH4zwQmwegjU1ucWgDtpVdukWRR/RMN1AhCC/xSbbyZ4CXi2SgiU1+EegLvpVd68I9R/Ni9kAnQNgXrzzQr+eHSFdx9VWqf0PcAr6tNAvb5R+GmauUFK06DqulI2cPYpyQxC9bUss3FmsZtXvf6vx4x+wGee10uPzaxW76HHzXjQZ1E3TcrvVsq8hKUHwKzenfNM2TeyEgHYdQpCduN3Uq8DqGyKN6V1SgXATGtzPKitT6qY0UqXBLXG7+QmwDPVTTtLeR2yhY0qTgPlxu/kCxxVCEKFxu/KFPqKUhgqNf1ZyaJHmUGo2vhd6eLfWfE1ey9LLeaT7E/hAgAAAAAAAAAAAAAQ6B/0/1izHDbaKwAAAABJRU5ErkJggg==';

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
