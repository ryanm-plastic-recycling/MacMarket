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
- Optional alerts via email/Slack

## 🛠️ To Do
- [ ] Decide on broker(s) to integrate
- [ ] Set up modular API wrapper framework
- [ ] Design signal schema (model + confidence + source)
- [ ] Design database schema for trades and logs
- [ ] Frontend wireframe for dashboard
- [ ] Develop risk and capital management module

## 🚧 Development Status
Exploratory phase — backend logic and LLM signal testing in progress. Confirming architecture before moving to live trading or frontend development.

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

### Running locally
1. Install Python dependencies using the consolidated requirements file in the
   project root:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up a MySQL database and load `schema.sql`.
3. Insert at least one user so alerts can be created:
   ```sql
   INSERT INTO users (email) VALUES ('test@example.com');
   ```
4. If upgrading from a previous version, create the `user_tickers` table to store custom ticker lists:
   ```sql
   CREATE TABLE user_tickers (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT NOT NULL,
       symbol VARCHAR(10) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
   );
   ```
5. Configure the `DATABASE_URL` environment variable if different from the default
   (`mysql+mysqlconnector://user:password@localhost:3306/macmarket`) defined in
   `backend/app/database.py`.
6. Start the API on your preferred port (e.g. 9500):
   ```bash
   uvicorn app:app --reload --port 9500
   ```
7. Navigate to `http://localhost:9500/index.html` for the main dashboard. The
   backend also serves `login.html`, `account.html`, and `tickers.html` so you can
   visit them directly via `/login.html`, `/account.html`, and `/tickers.html`.


## 🔍 Testing
This project uses `pytest` for testing. Sample tests validate the
health endpoint and confirm that the API can connect to MySQL.
To run the tests:

```bash
pip install -r requirements.txt  # install dependencies from the root file
pytest
```

The API exposes simple endpoints, including `/health` and `/db-check`.
