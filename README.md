# MacMarket: 🧠📈 AI-Powered Trading System

A next-generation trading platform that uses large language models (LLMs), market APIs, and news analysis to generate and execute trades across stocks, ETFs, and crypto.

## 📈 Purpose

This repository serves as the foundation for a smart trading system with the following goals:

- ✅ Analyze real-time market and news data
- ✅ Use LLMs (like ChatGPT) to generate trade insights
- ✅ Execute trades (simulated or real) using brokerage APIs
- ✅ Display trades, signals, and portfolio health via a clean, modern web interface

## 🧠 Core Concepts

### 1. **LLM + API Fusion**
Leverage ChatGPT and other LLMs to:
- Summarize financial headlines
- Parse earnings reports or Fed minutes
- Classify market sentiment
- Generate trading signals based on text + numerical data

### 2. **Multi-Source Market Data**
Aggregate feeds from:
- Stock APIs (e.g., Alpha Vantage, IEX Cloud, Yahoo Finance)
- Crypto exchanges (e.g., Coinbase, Binance)
- News APIs (e.g., NewsAPI, Google News)
- Social data (optional: Reddit, Twitter)

### 3. **Trade Execution Engine**
Planned support for:
- Paper trading (for strategy testing)
- Real trades via brokers (e.g., Alpaca, Robinhood, Interactive Brokers)

### 4. **Dashboard UI**
- Modern, mobile-friendly frontend
- View:
  - Live trades
  - Signal justifications
  - Portfolio value
  - Risk metrics (Sharpe, drawdown, etc.)
  - System logs and alerts

## 🏗️ Planned Stack
| Component    | Tech (Planned)                          |
|--------------|-----------------------------------------|
| Frontend     | React.js or plain HTML/JS (TBD)         |
| Backend      | Python (FastAPI or Flask) or Node.js    |
| LLM          | OpenAI ChatGPT API                      |
| Market Data  | Alpha Vantage, Binance API, etc.        |
| News Parsing | NewsAPI, GPT summarization              |
| Database     | MySQL                      |
| Hosting      | GitHub Pages (frontend), API hosted TBD |

## 📊 Key Features
- Signal generation based on:
  - News sentiment
  - Technical indicators
  - LLM interpretation of macroeconomic data
- Backtesting framework (WIP)
- Trade journal with rationale per trade
- API quota management
- Optional alerts via email/SMS
- Political trading data aggregation (QuiverQuant, Unusual Whales, Capitol Trades)

## 🛠️ To Do
- [ ] Decide on broker(s) to integrate
- [ ] Set up modular API wrapper framework
- [ ] Design signal schema (model + confidence + source)
- [ ] Design database schema for trades and logs
- [ ] Frontend wireframe for dashboard
- [ ] Develop risk and capital management module

## 🚧 Development Status
Exploratory phase — backend logic and LLM signal testing in progress. Confirming architecture before moving to live trading or frontend development.

## 🔄 Backtesting Signals
We provide a standalone backtester to validate signal performance offline.

**Prerequisites**
```bash
pip install -r requirements.txt
```

**Run the backtest**
```bash
python scripts/backtest_signals.py \
  --symbol AAPL \
  --start 2023-01-01 \
  --end   2025-07-01
# Follow whale or political trades from QuiverQuant instead of local signals
python scripts/backtest_signals.py \
  --symbol AAPL \
  --start 2023-01-01 \
  --end 2025-07-01 \
  --quiver whales
```

**Outputs**
- `backtest_results_AAPL.csv`: daily portfolio value and signal log
- `backtest_equity_AAPL.png`: cumulative equity curve
- Console summary of total return, CAGR, max drawdown, Sharpe ratio

Use this tool to validate any symbol’s LLM/API-generated signals before deploying live.
## 🧠 Ideas in the Pipeline
- LangChain or semantic memory for trade history
- Real-time news clustering and tagging
- Sector rotation model
- LLM-based anomaly detection

---

## 📬 Pre-Build Review Needed

Before we dive into building:
- Confirm your preferred broker and API for trading
- Choose backend stack (Python or Node)
- Frontend: clean HTML/JS or use a modern framework like React?
- Target hosting method (single server? split frontend/backend?)

Once locked in, we’ll begin building out core modules step-by-step.

## 🚀 Running the API
## Alert Preference System

This example includes a basic FastAPI backend and a very simple frontend page to manage alert preferences. The database schema is defined in `schema.sql`.
Email alerts use `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASS`. SMS alerts require `TWILIO_SID`, `TWILIO_TOKEN`, and `TWILIO_FROM`.

### Running locally
1. Install Python dependencies using the consolidated requirements file in the
   project root:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up a MySQL database and load `schema.sql`. Make sure the MySQL user
   specified in `DATABASE_URL` has permission to read and **update** the tables.
   The login endpoint updates the `last_logged_in` column, so a read-only
   account will cause a `503` error. A simple privilege setup is:
   ```sql
   GRANT SELECT, INSERT, UPDATE, DELETE ON macmarket.* TO 'your_user'@'localhost';
   ```

3. Copy `.env.example` to `.env` and update the values. Set `DATABASE_URL` to point
   at your MySQL instance, e.g. `mysql+mysqlconnector://user:pass@localhost:3306/macmarket`.

4. Insert at least one user with a username, hashed password, and TOTP secret. `otp_enabled` is set to `FALSE` by default so OTP is optional until enabled by the user:
   ```sql
   INSERT INTO users (username, password_hash, email, totp_secret, otp_enabled)
   VALUES
     ('demo', SHA2('password', 256), 'demo@example.com', 'JBSWY3DPEHPK3PXP', FALSE);
   ```
   You can generate a new TOTP secret with:
   ```bash
   python -c "import pyotp; print(pyotp.random_base32())"
   ```
5. The `user_tickers` table is included in `schema.sql` and stores custom ticker lists. If your
   database predates this table, create it with:
   ```sql
   CREATE TABLE user_tickers (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT NOT NULL,
       symbol VARCHAR(10) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
   );
   ```
   Generate a TOTP secret using:
   ```bash
   python -c "import pyotp; print(pyotp.random_base32())"
   ```
6. The `user_tickers` table defined in `schema.sql` stores custom ticker lists,
   so no additional setup is required.
   If your database was created before the `otp_enabled` column was added, run:
   ```sql
   ALTER TABLE users ADD COLUMN otp_enabled BOOLEAN DEFAULT FALSE;
   ```
7. Configure the `DATABASE_URL` environment variable if different from the default
   (`mysql+mysqlconnector://user:password@localhost:3306/macmarket`)
   defined in `backend/app/database.py`. Environment variables are loaded from a
   `.env` file automatically if present.
8. Optionally set `API_DAILY_QUOTA` to limit requests per IP (default `1000`).
   Set `OPENAI_API_KEY` to enable macro signal generation.
9. The login page uses Google reCAPTCHA (v2). The default site key is
   `key_here` and the default secret key is
   `secret_here`. You can override the secret by
   setting the `RECAPTCHA_SECRET` environment variable.
10. Start the API on your preferred port (e.g. 9500):
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 9500
   ```
11. Navigate to `http://localhost:9500/index.html` for the main dashboard. The
   backend also serves `login.html`, `account.html`, `tickers.html`, and `admin.html` so you can
   visit them directly via `/login.html`, `/account.html`, `/tickers.html`, and `/admin.html`.
12. Additional pages `signals.html` and `journal.html` provide interfaces for the
    signals, journal, positions, and recommendations endpoints.

### Risk Management Module

The `positions` table records open positions for each user. You can create it manually if
upgrading from an older database:

```sql
CREATE TABLE positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

The API exposes `/api/users/<id>/risk` which calculates exposure from these positions and
uses an LLM (if configured) to suggest potential actions.

### Signals, Journal, Positions, Recommendations, and Backtesting
Several additional endpoints are available:

* `GET /api/signals/<symbol>` &mdash; returns news sentiment and technical signals for a ticker.
* `POST /api/macro-signal` with a JSON body `{"text": "..."}` to interpret macroeconomic commentary via an LLM.
* `GET /api/backtest/<symbol>` &mdash; runs a simple SMA crossover backtest.
* `POST /api/backtest/<symbol>` &mdash; run a backtest and store the results.
* `GET /api/backtests` &mdash; list saved backtest runs (filterable by `user_id`).
* `GET /api/users/<id>/journal` and `POST /api/users/<id>/journal` &mdash; manage personal trade journal entries.
* `GET /api/users/<id>/positions` &mdash; list current positions for a user.
* `GET /api/users/<id>/recommendations` &mdash; provide simple trade recommendations based on the user's tickers.
* `GET /api/quiver/risk?symbols=AAPL,MSFT` &mdash; returns Quiver risk scores for the specified tickers (requires `QUIVER_API_KEY`).
* `GET /api/quiver/whales?limit=5` &mdash; lists recent whale moves limited to the given number (requires `QUIVER_API_KEY`).
* `GET /api/quiver/political?symbols=AAPL` &mdash; counts of recent congressional trades for the tickers (requires `QUIVER_API_KEY`).
* `GET /api/quiver/lobby?symbols=AAPL` &mdash; counts of recent lobbying disclosures for the tickers (requires `QUIVER_API_KEY`).

The frontend now includes `signals.html` and `journal.html` pages to interact with these endpoints.

### Optional Security Flags
You can disable certain login checks for local testing by setting environment
variables before starting the server:

* `DISABLE_CAPTCHA=1` &mdash; bypasses the reCAPTCHA challenge.
* `DISABLE_OTP=1` &mdash; bypasses TOTP verification.

Example:

```bash
DISABLE_CAPTCHA=1 DISABLE_OTP=1 uvicorn app:app --reload --host 0.0.0.0 --port 9500
```

### Managing users
* Log in with an admin account (set `is_admin` in the database or via the admin panel).
* The admin panel is available at `/admin.html` and lists all users.
* Use the panel to toggle admin rights or update user passwords.
* If you cannot log in, run `python change_password.py <id> <new_password>` to
  update the stored hash directly.
* Regular users can update their email via `PUT /api/users/<id>/email`.


## 🔍 Testing
This project uses `pytest` for testing. Sample tests validate the
health endpoint and confirm that the API can connect to MySQL.
To run the tests:

```bash
pip install -r requirements.txt  # install dependencies from the root file
pytest
```

The API exposes simple endpoints, including `/health` and `/db-check`.

## Disclaimers & Risk

### Paper Trading Only

- This project provides a **paper-trading** environment for strategy testing and education.
- Nothing in this repository constitutes financial advice or a solicitation to trade real funds.

### Backtest Assumptions

- Backtests cover a limited historical period and may not reflect future market conditions.
- Example parameters include simplified slippage and fee models; adjust these to match your broker.

### API Limits & Data Accuracy

- Data providers impose request quotas that can throttle or limit real-time updates.
- Quotes and historical data may be delayed or contain inaccuracies.

