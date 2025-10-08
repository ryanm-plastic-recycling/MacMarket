# MacMarket Architecture Overview

## Backend Stack
- **FastAPI (Python)**: `app.py` is the primary application. It loads environment variables, mounts the static `frontend/` assets, schedules background QuiverQuant tasks, and hosts the majority of REST endpoints (health, auth, tickers, journal, backtests, HACO signals, panorama, etc.). Supporting modules live in `backend/app/` (`crud.py`, `database.py`, `signals.py`, `risk.py`, `backtest.py`, `alerts.py`, `quotes.py`). Additional FastAPI entry points exist in `backend/app/main.py` (alerts microservice) and `backend/main.py` (demo `/market-data` route).
- **Express (Node.js)**: `server.js` duplicates large portions of the REST surface (`/api/panorama`, `/api/alerts`, `/api/signals/haco/scan`, tickers and scenario CRUD) while serving the same `frontend/` directory. Shared JavaScript service helpers live under `services/` (news, political, risk, alerts, whales, macro, crypto).
- **Routers**: `routes_alerts.py` (alerts CRUD + HACO worker) is included into `app.py`. `api/haco.py` exposes HACO scan endpoints at `/api/signals/haco`. `api/qq_routes.py` mounts QuiverQuant ingestion APIs at `/api/qq` and is scheduled from `app.py`.
- **Indicator & data modules**: Indicator logic resides in `indicators/haco.py` (imported by both routers and the alerts worker). `backend/app/signals.py` aggregates NewsAPI, QuiverQuant, Unusual Whales, and yfinance data. `backend/app/quotes.py` wraps yfinance price lookups. Express services under `services/` hit the same vendors via Axios.
- **Tests**: Pytest suite under `tests/` covers HACO math, API responses, database access, journal, and panorama aggregations.
- **Dependencies**: Python dependencies are listed in `requirements.txt`; Node dependencies in `package.json`.

## Frontend Assets
- **Static HTML bundle**: Legacy multipage UI in `frontend/` (`index.html`, `alerts.html`, `signals.html`, etc.) with scripts in `frontend/js/` and CSS in `frontend/style.css`/`TopCongressBuysWidget.css`. FastAPI mounts this folder at `/` and separately mounts `/js` and `/static` (`static/js` includes Lightweight Charts bundle).
- **React app**: `src/` contains a React Router SPA (`App.jsx`, components, `pages/TickersPage.jsx`). No build output is committed; if built it would land in `frontend/build/` (app.py checks for it).
- **Additional content**: `pages/newsletter/[date].mdx` (likely for Next.js/MDX newsletters) and `public/journal.html` + `public/js/journal.js` for embeddable widgets.
- **Charting**: Lightweight Charts is shipped locally via `static/js/lightweight-charts.standalone.production.js`; `package.json` also includes `chart.js`.

## Configuration & Deployment
- No committed `.env`; configuration happens through environment variables (`dotenv.load_dotenv()` in `app.py`) and `config.yaml` (strategy tester defaults). There are no Docker/Procfile assets. Windows launchers (`start-macmarket.bat`, `uvicorn/` scripts) start the FastAPI app.

## Endpoint Inventory & Static Serving
- 100+ REST endpoints exist today: FastAPI handles `/api/signals/{symbol}`, `/api/alerts`, `/api/watchlist` (`/api/users/{user_id}/tickers`), `/api/qq/*`, `/api/panorama`, `/strategy-test/*`, etc. Express duplicates many of the same paths plus `/api/tickers`, `/api/scenarios`, and `/api/signals/haco/scan`. See `ARCHITECTURE.json` for the machine-readable list with file locations.
- Static delivery is handled by FastAPI (`app.mount("/", StaticFiles(directory=frontend))`, `/static`, `/js`) and Express (`express.static(frontend)` with `/static` alias). There is currently **no** `/web/*` route; any new `web/` assets would not be served without wiring.

## Overlaps & Risks
- There are three backend entry points (`app.py`, `backend/app/main.py`, `server.js`) serving overlapping functionality. Alert routers, HACO services, and indicator logic already exist—new `backend/app/routers/*`, `backend/app/services/*`, `backend/app/indicators/*`, or `web/*` additions would duplicate these.
- Keeping FastAPI and Express code paths in sync is error-prone: both maintain separate MySQL access layers, HACO scan endpoints, and alerts CRUD semantics.
- Consolidation should pick a single FastAPI surface (`app.py`) and fold new code into existing modules to avoid diverging APIs or double scheduling/cron work.
