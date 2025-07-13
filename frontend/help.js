const helpContent = {
  index: `
    <h2>Dashboard</h2>
    <p>The dashboard shows market data. The scrolling ticker displays prices for your saved symbols. Click <strong>Pause</strong> to stop the scroll.</p>
    <p>Tiles underneath show the latest price and percent change for the first four tickers plus BTC and ETH.</p>
    <h3>Alerts</h3>
    <p>The alerts list shows the latest signals from data sources. Example output:<br><code>ALERT: SPY bullish breakout</code></p>
    <h3>Political Trading Activity</h3>
    <p>Shows recent congressional trades from QuiverQuant.</p>
    <h3>News</h3>
    <p>Select a range (7 days, 30 days or All) to filter the market and world news feeds.</p>
  `,
  login: `
    <h2>Login</h2>
    <p>Enter your account credentials and optionally a one time password.</p>
    <pre>Username: demo\nPassword: yourpass\nOTP: 123456</pre>
    <p>On success you are redirected to your account page.</p>
  `,
  account: `
    <h2>Account</h2>
    <p>Change your username, email or password. Check <em>Enable OTP</em> to require a one time password when logging in.</p>
    <p>Example: update email then click <strong>Save</strong> to submit.</p>
  `,
  tickers: `
    <h2>Manage Tickers</h2>
    <p>Use the table to select the symbols you want across the site. Add tickers with the input box, drag to reorder and click <strong>Save</strong>.</p>
    <p>Example input: <code>NVDA</code> then press <strong>Add</strong>.</p>
  `,
  signals: `
    <h2>Signals</h2>
    <p><strong>Symbol Signal</strong> fetches news sentiment and a moving-average based technical signal.</p>
    <p>Example input: <code>AAPL</code> then click <strong>Get Signal</strong>. The response shows sentiment score and technical trend.</p>
    <p><strong>Macro Outlook</strong> analyzes pasted text with an LLM.</p>
    <p><strong>Recommendations</strong> loads suggestions for your saved tickers.</p>
    <p><strong>Get Recommendation for Symbol</strong> queries a specific ticker.</p>
  `,
  journal: `
    <h2>Journal</h2>
    <p>Review past trades and current positions. Fill out the form to add a new entry.</p>
    <p>Example: symbol <code>AAPL</code>, action <code>buy</code>, quantity <code>10</code>, price <code>150</code>, then click <strong>Add</strong>. The new entry appears in the table.</p>
  `,
  backtests: `
    <h2>Backtests</h2>
    <p>Run a simple historical test of a trading strategy.</p>
    <p>Example: symbol <code>SPY</code>, start <code>2023-01-01</code>, end <code>2024-01-01</code>, then click <strong>Run</strong>. The results appear in JSON and are saved in the table.</p>
  `,
  admin: `
    <h2>Admin Panel</h2>
    <p>Manage users and test API integrations. Edit user details in the table and click <strong>Save</strong>.</p>
    <p>The API tester lets you send a request to each configured endpoint and view the response.</p>
  `,
  github: `
    <h2>GitHub</h2>
    <p>This page shows a link to the project repository and the README contents loaded from the server.</p>
  `
};

function initHelp(page){
  const header = document.querySelector('header');
  if(!header) return;
  const btn = document.createElement('button');
  btn.id = 'help-btn';
  btn.className = 'help-button';
  btn.textContent = '?';
  header.appendChild(btn);

  const overlay = document.createElement('div');
  overlay.id = 'help-overlay';
  overlay.innerHTML = '<div class="help-content"><button id="help-close">Close</button><div id="help-body"></div></div>';
  document.body.appendChild(overlay);
  btn.addEventListener('click', () => {
    document.getElementById('help-body').innerHTML = helpContent[page] || '';
    overlay.style.display = 'block';
  });
  document.getElementById('help-close').addEventListener('click', () => {
    overlay.style.display = 'none';
  });
}
