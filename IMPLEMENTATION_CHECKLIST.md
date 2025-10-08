# Consolidation Execution Checklist

1. **Create branch** `chore/consolidate-signals-backend` from `work`.
2. **Decide canonical backend**:
   - Keep `app.py` as the only FastAPI entry point.
   - Remove Express duplication after migrating any unique endpoints into FastAPI.
3. **Unify indicators**:
   - Move any new indicator code into `indicators/haco.py` (or sibling modules inside `indicators/`).
   - Update imports to use `from indicators import haco` throughout (`api/haco.py`, `routes_alerts.py`, tests).
4. **Merge service logic**:
   - Fold Python service helpers into `backend/app/signals.py`, `alerts.py`, `backtest.py`, or `risk.py` rather than creating `backend/app/services/*`.
   - Decommission duplicated JS services if FastAPI fully replaces Express endpoints, but retain Node utilities (e.g., `discord_bot.js`) as needed.
5. **Router wiring**:
   - Extend existing routers (`routes_alerts.py`, `api/haco.py`, `api/qq_routes.py`) with any new endpoints instead of creating `backend/app/routers/*`.
   - Ensure routers are included in `app.py` and share the same database/session dependencies.
6. **Integrate watchlist & alerts endpoints**:
   - Confirm `/api/alerts`, `/api/signals/{symbol}`, and `/api/watchlist` (`/api/users/{user_id}/tickers`) continue to resolve via FastAPI after the merge.
7. **Normalize chart timestamps**:
   - Update HACO scan responses (FastAPI) to emit epoch seconds for Lightweight Charts and adjust frontend parsing if necessary.
8. **Static assets**:
   - Keep signals UI inside `frontend/` and `static/`. If new designs are required, replace `frontend/signals.html` & supporting JS/CSS directly; avoid introducing a `web/` directory unless `app.py` mounts it.
9. **Dependencies**:
   - Merge any Python requirements into the root `requirements.txt` and reconcile Node dependencies in `package.json` if Express is retired.
10. **Testing & validation**:
    - Run `pytest` to ensure backend tests remain green.
    - Manually verify `/api/signals/{symbol}`, `/api/alerts`, `/api/watchlist`, and HACO chart endpoints return the expected payload shape.
11. **Clean up**:
    - Delete superseded modules (`backend/app/main.py`, Express-specific duplicates) once traffic is confirmed on FastAPI.
    - Update documentation/README to explain the single FastAPI deployment path.
