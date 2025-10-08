# Signals Backend Consolidation Plan

| Component | New File/Path | Existing File/Path | Proposed Action | Notes / Risks |
|-----------|---------------|--------------------|-----------------|---------------|
| HACO indicator logic | `backend/app/indicators/*` | `indicators/haco.py` (imported by `api/haco.py`, `routes_alerts.py`) | **Reuse existing** indicator module; export a single `indicators` package and delete duplicate copy once imports updated. | Existing tests (`tests/test_haco.py`) cover `indicators/haco.py`. Duplicating risks divergence and extra maintenance. |
| Signals/alerts services | `backend/app/services/*` (Python) | `backend/app/signals.py`, `backend/app/alerts.py`, `backend/app/backtest.py`, plus Express helpers in `services/*.js` | **Move new code into existing modules** (`backend/app/signals.py` & friends) instead of a parallel services tree. | Keeps FastAPI + alert worker using one implementation; ensure async HTTP clients share TTL caches already configured in `app.py`. |
| API routers | `backend/app/routers/*` | `routes_alerts.py`, `api/haco.py`, `api/qq_routes.py` (already mounted) | **Reuse existing routers**; extend them with new endpoints if needed. | Adding another router tree will require duplicate dependency wiring (DB sessions, background tasks). |
| FastAPI entry point | `backend/app/main.py` | `app.py` (canonical), `backend/app/main.py` (duplicate), `server.js` (Express) | **Adopt `app.py` as single FastAPI app**; migrate any unique logic from `backend/app/main.py` before deleting it. | `app.py` already mounts templates, static assets, routers, scheduler. Removing duplicates prevents double table creation/startup side effects. |
| Legacy Express APIs | `server.js` (existing Node) | `app.py` FastAPI equivalents | **Fold Express-only routes into FastAPI** then retire Node server. | Ensure MySQL access patterns (pool vs SQLAlchemy) are mapped; keep Discord bot or other Node utilities unaffected. |
| Static signals page | `web/signals.html`, `web/js/signals.js`, `web/css/indicators.css` | `frontend/signals.html`, `frontend/js/haco*.js`, `static/js/lightweight-charts...`, `frontend/style.css` | **Reuse existing `frontend/` assets**; if new design is required, update files in place. | FastAPI/Express currently only mount `frontend/` and `static/`; a new `web/` folder would not be served without additional mounts. |

## Additional Notes
- `/api/signals/{symbol}`, `/api/alerts`, and `/api/watchlist` (`/api/users/{user_id}/tickers`) already exist in `app.py`. Preserve these signatures while consolidating.
- Any new indicator helpers should live under a single `indicators/` package to keep import paths stable for routers, worker, and tests.

## PR Plan
- **Branch**: `chore/consolidate-signals-backend`
- **Atomic commits**:
  1. Move indicator/service/router code into existing FastAPI modules (`indicators/`, `backend/app/*.py`, `routes_alerts.py`).
  2. Wire consolidated routers into `app.py` and delete redundant FastAPI entry points.
  3. Normalize Lightweight Charts payloads (epoch seconds) and align frontend consumers.
  4. Ensure `/web` assets are served or document build pipeline; keep static mounts consistent.
  5. Merge Python `requirements.txt` updates (and Node dependencies if Express removal touches them).
  6. Update/repair tests and imports, run `pytest` (and JS lint/build if applicable).
- **Breaking changes**: None expected—retain `/api/signals/{symbol}`, `/api/alerts`, `/api/watchlist` behavior.
