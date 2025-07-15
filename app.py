from fastapi import FastAPI, HTTPException, Depends
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from sqlalchemy.exc import SQLAlchemyError
from backend.app.database import connect_to_db, SessionLocal, engine
from backend.app import database as db_module
from sqlalchemy.orm import Session
from backend.app import models, crud, schemas
import backend.app.security as security
from backend.app import risk
import pyotp
from backend.app import signals, backtest, alerts
from backend.app.signals import format_price, fetch_unusual_whales
from datetime import datetime
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import os

# simple in-memory alert store
LATEST_ALERT = {"id": 0, "ticker": "AAPL", "price": 0.0}

from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import yfinance as yf
import requests
from macmarket import strategy_tester as st
import pandas as pd
import asyncio
import httpx
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

# Caching configuration
NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "300"))
POLITICAL_CACHE_TTL = int(os.getenv("POLITICAL_CACHE_TTL", "300"))

app = FastAPI()

# Initialize caches only if TTL > 0 so caching can be disabled via env vars
political_cache = TTLCache(maxsize=1, ttl=POLITICAL_CACHE_TTL) if POLITICAL_CACHE_TTL > 0 else None
news_cache = TTLCache(maxsize=2, ttl=NEWS_CACHE_TTL) if NEWS_CACHE_TTL > 0 else None
quiver_cache = TTLCache(maxsize=10, ttl=300)

# Serve React build if present
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
REACT_BUILD_DIR = FRONTEND_DIR / "build"
if REACT_BUILD_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=REACT_BUILD_DIR, html=True),
        name="static",
    )

class QuotaMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limit = int(os.getenv("API_DAILY_QUOTA", "1000"))
        self.counts = {}
        self.day = datetime.utcnow().date()

    async def dispatch(self, request: Request, call_next):
        current = datetime.utcnow().date()
        if current != self.day:
            self.counts = {}
            self.day = current
        ip = request.client.host
        self.counts[ip] = self.counts.get(ip, 0) + 1
        if self.counts[ip] > self.limit:
            return Response("API quota exceeded", status_code=429)
        return await call_next(request)

app.add_middleware(QuotaMiddleware)
try:
    models.Base.metadata.create_all(bind=engine)
except Exception:
    # Database might be unavailable during testing
    pass

# Directory containing the HTML frontend files
# (retained for legacy direct HTML endpoints)
# FRONTEND_DIR already defined above

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    """Simple health check."""
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    """Check database connectivity."""
    try:
        conn = db_module.connect_to_db()
        conn.close()
        return {"status": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the main frontend page."""
    if REACT_BUILD_DIR.is_dir():
        return FileResponse(REACT_BUILD_DIR / "index.html")
    html_path = FRONTEND_DIR / "index.html"
    return html_path.read_text()


@app.get("/api/ticker")
def ticker_data(symbols: str):
    """Return basic market data for given comma separated tickers."""
    tickers = symbols.split(",")
    data = []
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            info = t.info
            price = info.get("regularMarketPrice")
            change = info.get("regularMarketChangePercent")
            if price is None or change is None:
                hist = t.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                    change = (price - prev) / prev * 100 if prev else 0
            price = format_price(price) if price is not None else None
            data.append({"symbol": symbol, "price": price, "change_percent": change})
        except Exception:
            data.append({"symbol": symbol, "price": None, "change_percent": None})
    return {"data": data}


@app.get("/api/history")
def price_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    """Return historical close prices for a symbol."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period=period, interval=interval)
        if hist.empty:
            raise ValueError("no data")
        hist = hist.reset_index()
        date_col = hist.columns[0]
        dates = [d.strftime("%Y-%m-%d") for d in hist[date_col]]
        closes = [float(c) if pd.notna(c) else None for c in hist["Close"]]
        return {"symbol": symbol, "dates": dates, "close": closes}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/price/{symbol}")
def current_price(symbol: str):
    """Return the latest price for a symbol."""
    price = signals._current_price(symbol)
    if price is None:
        raise HTTPException(status_code=404, detail="Price unavailable")
    return {"symbol": symbol, "price": format_price(price)}


@app.get("/api/news")
async def news(age: str = "week"):
    """Fetch finance and world news articles from multiple sources."""
    if news_cache is not None and age in news_cache:
        return news_cache[age]

    market: list[dict] = []
    world: list[dict] = []

    async with httpx.AsyncClient(timeout=10) as client:
        hn_task = client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "market", "tags": "story"},
        )
        rss_urls = [
            ("https://feeds.foxnews.com/foxnews/business", market),
            ("https://www.bloomberg.com/feed/podcast/etf-report.xml", market),
            ("https://feeds.foxbusiness.com/foxbusiness/markets", market),
            ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml", world),
            ("https://feeds.bbci.co.uk/news/world/rss.xml", world),
        ]
        rss_tasks = [client.get(url) for url, _ in rss_urls]
        responses = await asyncio.gather(hn_task, *rss_tasks, return_exceptions=True)

    hn_resp = responses[0]
    if isinstance(hn_resp, httpx.Response) and hn_resp.status_code == 200:
        try:
            market.extend(
                [
                    {"title": h.get("title"), "url": h.get("url"), "date": h.get("created_at")}
                    for h in hn_resp.json().get("hits", [])[:5]
                ]
            )
        except Exception:
            pass

    for resp, (_url, dest) in zip(responses[1:], rss_urls):
        if isinstance(resp, httpx.Response) and resp.status_code == 200:
            try:
                from xml.etree import ElementTree

                root = ElementTree.fromstring(resp.content)
                for item in root.findall('.//item')[:5]:
                    title = item.findtext('title')
                    link = item.findtext('link')
                    date = item.findtext('pubDate')
                    if title and link:
                        dest.append({"title": title, "url": link, "date": date})
            except Exception:
                pass

    if age in {"week", "month"}:
        days = 7 if age == "week" else 30

        def filter_articles(articles, days=7):
            from datetime import datetime, timedelta, timezone
            import dateutil.parser

            # Create a UTC-aware cutoff timestamp
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = []

            for item in articles:
                # Parse the article date and normalize to UTC
                dt = dateutil.parser.parse(item['date'])
                if dt.tzinfo is None:
                    # Assume UTC if no timezone provided
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)

                # Compare two UTC-aware datetimes
                if dt >= cutoff:
                    filtered.append(item)

            return filtered

        market[:] = filter_articles(market, days=days)
        world[:] = filter_articles(world, days=days)

    result = {"market": market, "world": world}
    if news_cache is not None:
        news_cache[age] = result
    return result


@app.get("/api/political")
async def political():
    """Fetch trading data from political/congressional sources."""
    if political_cache is not None and "data" in political_cache:
        return political_cache["data"]

    data = {"quiver": [], "whales": [], "capitol": []}

    quiver_headers = {"Authorization": f"Bearer {os.getenv('QUIVER_API_KEY')}"} if os.getenv("QUIVER_API_KEY") else {}
    whales_headers = {"Authorization": f"Bearer {os.getenv('WHALES_API_KEY')}"} if os.getenv("WHALES_API_KEY") else {}
    capitol_headers = {"Authorization": f"Bearer {os.getenv('CAPITOL_API_KEY')}"} if os.getenv("CAPITOL_API_KEY") else {}

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [
            client.get("https://api.quiverquant.com/beta/live/congresstrading", headers=quiver_headers),
            client.get("https://api.unusualwhales.com/congress/trades", headers=whales_headers),
            client.get(
                "https://api.capitoltrades.com/trades",
                headers=capitol_headers,
                params={"limit": 5},
            ),
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    quiver_resp, whales_resp, capitol_resp = responses

    if isinstance(quiver_resp, httpx.Response) and quiver_resp.status_code == 200:
        try:
            data["quiver"] = quiver_resp.json()[:5]
        except Exception:
            pass
    if isinstance(whales_resp, httpx.Response) and whales_resp.status_code == 200:
        try:
            resp = whales_resp.json()
            data["whales"] = resp.get("results", resp)[:5] if isinstance(resp, dict) else resp[:5]
        except Exception:
            pass
    if isinstance(capitol_resp, httpx.Response) and capitol_resp.status_code == 200:
        try:
            resp = capitol_resp.json()
            data["capitol"] = resp.get("data", resp)[:5] if isinstance(resp, dict) else resp[:5]
        except Exception:
            pass

    if political_cache is not None:
        political_cache["data"] = data

    return data


@app.get("/api/quiver/risk")
async def quiver_risk(symbols: str):
    """Return Quiver risk factors for the given symbols."""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    key = tuple(sorted(syms))
    if key in quiver_cache:
        return {"risk": quiver_cache[key]}
    data = signals.get_risk_factors(syms)
    quiver_cache[key] = data
    return {"risk": data}


@app.get("/api/quiver/whales")
async def quiver_whales(limit: int = 5):
    """Return recent whale moves from Quiver."""
    key = f"whales-{limit}"
    if key in quiver_cache:
        return {"whales": quiver_cache[key]}
    data = signals.get_whale_moves(limit)
    quiver_cache[key] = data
    return {"whales": data}


@app.get("/api/quiver/political")
async def quiver_political(symbols: str):
    """Return counts of recent congressional trades for the given symbols."""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    key = ("political",) + tuple(sorted(syms))
    if key in quiver_cache:
        return {"political": quiver_cache[key]}
    data = signals.get_political_moves(syms)
    quiver_cache[key] = data
    return {"political": data}


@app.get("/api/quiver/lobby")
async def quiver_lobby(symbols: str):
    """Return counts of recent lobbying disclosures for the given symbols."""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    key = ("lobby",) + tuple(sorted(syms))
    if key in quiver_cache:
        return {"lobby": quiver_cache[key]}
    data = signals.get_lobby_disclosures(syms)
    quiver_cache[key] = data
    return {"lobby": data}


@app.get("/api/panorama")
async def panorama(symbols: str = "AAPL,MSFT,GOOGL,AMZN,TSLA,SPY,QQQ,GLD,BTC-USD,ETH-USD", limit: int = 5):
    """Return aggregated market data used by the dashboard."""
    market = ticker_data(symbols)["data"]

    alerts_task = fetch_unusual_whales(limit=limit)
    political_task = political()
    risk_task = quiver_risk(symbols)
    whales_task = quiver_whales(limit=limit)
    news_task = news()

    alerts, political_data, risk_resp, whales_resp, news_data = await asyncio.gather(
        alerts_task, political_task, risk_task, whales_task, news_task
    )
    risk = risk_resp["risk"]
    whales = whales_resp["whales"]
    return {
        "market": market,
        "alerts": alerts,
        "political": political_data,
        "risk": risk,
        "whales": whales,
        "news": news_data,
    }


@app.post("/api/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user account and return the TOTP secret."""
    if not security.verify_recaptcha(user.captcha_token):
        raise HTTPException(status_code=401, detail="Invalid captcha")
    try:
        db_user = crud.create_user(db, user.username, user.password, user.email)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"user_id": db_user.id, "totp_secret": db_user.totp_secret}


@app.post("/api/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    """Authenticate an existing user."""
    if os.getenv("DISABLE_CAPTCHA", "").lower() not in {"1", "true", "yes"}:
        if not security.verify_recaptcha(user.captcha_token or ""):
            raise HTTPException(status_code=401, detail="Invalid captcha")
    try:
        db_user = crud.authenticate_user(db, user.username, user.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except SQLAlchemyError:
        # Any database failure when retrieving the user should result in a 503
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable"
        )
    if (
        os.getenv("DISABLE_OTP", "").lower() not in {"1", "true", "yes"}
        and db_user.otp_enabled
    ):
        totp = pyotp.TOTP(db_user.totp_secret)
        if not totp.verify(user.otp or ""):
            raise HTTPException(status_code=401, detail="Invalid OTP")
    crud.update_last_login(db, db_user.id)
    return {"user_id": db_user.id, "username": db_user.username, "is_admin": db_user.is_admin}


@app.post("/api/logout")
def logout():
    """Placeholder logout endpoint."""
    return {"status": "logged out"}


@app.get("/api/users/{user_id}/tickers")
def get_user_tickers(user_id: int, db: Session = Depends(get_db)):
    """Return the list of tickers for a user."""
    tickers = crud.get_tickers(db, user_id)
    return {"tickers": [t.symbol for t in tickers]}


@app.put("/api/users/{user_id}/tickers")
def update_user_tickers(user_id: int, ticker_list: schemas.TickerList, db: Session = Depends(get_db)):
    """Replace a user's tickers with the provided list."""
    crud.set_user_tickers(db, user_id, ticker_list.tickers)
    return {"tickers": ticker_list.tickers}


@app.put("/api/users/{user_id}/email")
def update_user_email(user_id: int, email: schemas.EmailUpdate, db: Session = Depends(get_db)):
    """Update the email address for a user."""
    user = crud.set_user_email(db, user_id, email.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user.email}


@app.put("/api/users/{user_id}/password")
def update_user_password(user_id: int, pw: schemas.PasswordUpdate, db: Session = Depends(get_db)):
    """Allow a user to change their own password."""
    user = crud.set_user_password(db, user_id, pw.password)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "updated"}


@app.put("/api/users/{user_id}/username")
def update_username(user_id: int, data: schemas.UsernameUpdate, db: Session = Depends(get_db)):
    """Allow a user to change their username."""
    try:
        user = crud.set_username(db, user_id, data.username)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.username}


@app.put("/api/users/{user_id}/otp")
def update_otp(user_id: int, data: schemas.OtpUpdate, db: Session = Depends(get_db)):
    """Enable or disable OTP for a user. Returns the secret when enabling."""
    user = crud.set_otp_enabled(db, user_id, data.otp_enabled)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    resp = {"otp_enabled": user.otp_enabled}
    if user.otp_enabled:
        resp["totp_secret"] = user.totp_secret
    return resp


@app.get("/api/users/{user_id}/risk")
def get_user_risk(user_id: int, db: Session = Depends(get_db)):
    """Return basic risk metrics and LLM suggestions for a user."""
    positions = risk.get_positions(db, user_id)
    exposure = risk.calculate_exposure(positions)
    summary = f"User {user_id} portfolio exposure: {exposure}"
    suggestion = risk.llm_suggestion(summary)
    return {"exposure": exposure, "suggestion": suggestion}


@app.get("/api/users/{user_id}/positions")
def get_user_positions(user_id: int, db: Session = Depends(get_db)):
    """Return all open positions for the user."""
    positions = risk.get_positions(db, user_id)
    data = [
        {"symbol": p.symbol, "quantity": float(p.quantity), "price": float(p.price)}
        for p in positions
    ]
    return {"positions": data}


@app.get("/api/users/{user_id}/recommendations")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Provide simple trade recommendations for the user's tickers."""
    tickers = crud.get_tickers(db, user_id)
    symbols = [t.symbol for t in tickers] if tickers else ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    recs = signals.generate_recommendations(symbols)
    return {"recommendations": recs}


@app.get("/api/recommendation/{symbol}")
def recommendation_for_symbol(symbol: str):
    """Return a recommendation for a single symbol."""
    recs = signals.generate_recommendations([symbol])
    if not recs:
        raise HTTPException(status_code=404, detail="No recommendation")
    return {"recommendation": recs[0]}


@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db)):
    """Return all users for admin management."""
    users = crud.get_users(db)
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.is_admin,
                "otp_enabled": u.otp_enabled,
                "last_logged_in": u.last_logged_in.isoformat() if u.last_logged_in else None,
            }
            for u in users
        ]
    }


@app.put("/api/admin/users/{user_id}/password")
def admin_update_password(user_id: int, pw: schemas.PasswordUpdate, db: Session = Depends(get_db)):
    """Set a new password for a user."""
    user = crud.set_user_password(db, user_id, pw.password)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "updated"}


@app.put("/api/admin/users/{user_id}/admin")
def admin_toggle(user_id: int, is_admin: bool, db: Session = Depends(get_db)):
    """Update admin flag for a user."""
    user = crud.set_admin_status(db, user_id, is_admin)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "updated", "is_admin": user.is_admin}


@app.put("/api/admin/users/{user_id}/email")
def admin_update_email(user_id: int, data: schemas.EmailUpdate, db: Session = Depends(get_db)):
    """Update a user's email from the admin panel."""
    user = crud.set_user_email(db, user_id, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user.email}


@app.put("/api/admin/users/{user_id}/username")
def admin_update_username(user_id: int, data: schemas.UsernameUpdate, db: Session = Depends(get_db)):
    """Update a user's username from the admin panel."""
    try:
        user = crud.set_username(db, user_id, data.username)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.username}


@app.put("/api/admin/users/{user_id}/otp")
def admin_update_otp(user_id: int, data: schemas.OtpUpdate, db: Session = Depends(get_db)):
    """Enable or disable OTP for a user via the admin panel."""
    user = crud.set_otp_enabled(db, user_id, data.otp_enabled)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    resp = {"otp_enabled": user.otp_enabled}
    if user.otp_enabled:
        resp["totp_secret"] = user.totp_secret
    return resp


@app.post("/api/users/{user_id}/journal", response_model=schemas.JournalEntry)
def create_journal(user_id: int, entry: schemas.JournalEntryCreate, db: Session = Depends(get_db)):
    return crud.create_journal_entry(db, user_id, entry.symbol, entry.action, entry.quantity, entry.price, entry.rationale)

@app.get(
    "/api/users/{user_id}/journal",
    response_model=list[schemas.JournalEntryWithRec],
)
def read_journal(
    user_id: int,
    include_recs: bool = False,
    db: Session = Depends(get_db),
):
    """Return journal entries with optional recommendations."""
    entries = crud.get_journal_entries(db, user_id)
    if include_recs:
        for e in entries:
            recs = signals.generate_recommendations([e.symbol])
            e.recommendation = recs[0] if recs else None
    else:
        for e in entries:
            e.recommendation = None
    return entries


@app.put("/api/users/{user_id}/journal/{entry_id}", response_model=schemas.JournalEntry)
def update_journal(user_id: int, entry_id: int, data: schemas.JournalEntryUpdate, db: Session = Depends(get_db)):
    entry = crud.get_journal_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return crud.update_journal_entry(db, entry, data)


@app.delete("/api/users/{user_id}/journal/{entry_id}")
def delete_journal(user_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = crud.get_journal_entry(db, user_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    crud.delete_journal_entry(db, entry)
    return {"status": "deleted"}

@app.get(
    "/api/signals/rankings",
    responses={200: {"content": {"application/json": {}, "text/csv": {}}}},
)
def signal_rankings(format: str = "json"):
    """Return rankings of active signal scores."""
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    recs = signals.generate_recommendations(symbols)
    ranks = [{"symbol": r["symbol"], "score": r["probability"]} for r in recs]
    ranks.sort(key=lambda x: x["score"], reverse=True)
    if format.lower() == "csv":
        lines = ["symbol,score"] + [f"{r['symbol']},{r['score']}" for r in ranks]
        return Response("\n".join(lines), media_type="text/csv")

    return {"rankings": ranks}

@app.get("/api/signals/{symbol}")
def get_signals(symbol: str):
    news = signals.news_sentiment_signal(symbol)
    tech = signals.technical_indicator_signal(symbol)
    return {"news": news, "technical": tech}

@app.post("/api/macro-signal")
def macro_signal(data: dict):
    return signals.macro_llm_signal(data.get("text", ""))

@app.get("/api/backtest/{symbol}")
def run_backtest(symbol: str, start: str = "2023-01-01", end: str | None = None):
    """Run a backtest for the given symbol and return results."""
    return backtest.sma_crossover_backtest(symbol, start=start, end=end)


@app.post("/api/backtest/{symbol}", response_model=schemas.BacktestRun)
def save_backtest(
    symbol: str,
    start: str = "2023-01-01",
    end: str | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Run a backtest and save the result for later comparison."""
    res = backtest.sma_crossover_backtest(symbol, start=start, end=end)
    run = crud.create_backtest_run(db, symbol, start, end or datetime.utcnow().strftime("%Y-%m-%d"), res["metrics"], user_id)
    run.metrics = res["metrics"]  # convert JSON string back
    return run


@app.get("/api/backtests", response_model=list[schemas.BacktestRun])
def list_backtests(user_id: int | None = None, db: Session = Depends(get_db)):
    """Return saved backtest runs."""
    try:
        runs = crud.get_backtest_runs(db, user_id)
    except SQLAlchemyError:
        return []
    for r in runs:
        r.metrics = json.loads(r.metrics)
    return runs

@app.get("/strategy-test/list")
def list_strategy_keys():
    return st.list_strategies()


@app.post("/strategy-test/run")
def run_strategy(payload: dict):
    strategy = payload.get("strategy")
    user_id = payload.get("user_id")
    if not strategy or user_id is None:
        raise HTTPException(status_code=400, detail="missing params")
    metrics = st.run_strategy(strategy)
    st.record_run(int(user_id), strategy, payload.get("params", {}), metrics)
    return metrics


@app.get("/strategy-test/history")
def strategy_history(user_id: int):
    return st.get_history(user_id)


@app.get("/api/signals/alert")
async def latest_alert():
    """Return recent whale alerts."""
    alerts = await fetch_unusual_whales()
    return alerts


@app.post("/api/signals/alert")
def update_alert(alert: dict):
    """Update the latest trading alert."""
    global LATEST_ALERT
    LATEST_ALERT = {
        "id": int(alert.get("id", LATEST_ALERT["id"] + 1)),
        "ticker": alert.get("ticker", LATEST_ALERT.get("ticker")),
        "price": float(alert.get("price", LATEST_ALERT.get("price", 0.0))),
    }
    return {"status": "ok"}


@app.get("/api/crypto")
def crypto(limit: int = 5):
    """Return top crypto market data from Coingecko."""
    endpoint = os.getenv("COINGECKO_ENDPOINT", "https://api.coingecko.com/api/v3")
    url = f"{endpoint}/coins/markets"
    try:
        r = requests.get(
            url,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
            },
            timeout=10,
        )
        if r.ok:
            return {"data": r.json()}
    except Exception as exc:  # pragma: no cover - network
        raise HTTPException(status_code=500, detail=str(exc))
    raise HTTPException(status_code=502, detail="API error")


@app.get("/api/macro")
def macro():
    """Return recent PPI data from FRED."""
    key = os.getenv("FRED_API_KEY")
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "PPIACO",
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 12,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.ok:
            data = r.json().get("observations", [])
            return {"data": data}
    except Exception as exc:  # pragma: no cover - network
        raise HTTPException(status_code=500, detail=str(exc))
    raise HTTPException(status_code=502, detail="API error")


@app.get("/api/signals/{symbol}")
def get_signals(symbol: str):
    news = signals.news_sentiment_signal(symbol)
    tech = signals.technical_indicator_signal(symbol)
    return {"news": news, "technical": tech}

@app.post("/api/macro-signal")
def macro_signal(data: dict):
    return signals.macro_llm_signal(data.get("text", ""))

@app.get("/api/backtest/{symbol}")
def run_backtest(symbol: str):
    return backtest.sma_crossover_backtest(symbol)

# Serve static assets for the simple frontend
@app.get("/style.css")
def style_css():
    css_file = FRONTEND_DIR / "style.css"
    if css_file.exists():
        return Response(css_file.read_text(), media_type="text/css")
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/theme.js")
def theme_js():
    js_file = FRONTEND_DIR / "theme.js"
    if js_file.exists():
        return Response(js_file.read_text(), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not Found")

# Additional static assets for the simple frontend
@app.get("/ticker.js")
def ticker_js():
    js_file = FRONTEND_DIR / "ticker.js"
    if js_file.exists():
        return Response(js_file.read_text(), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/Dashboard.jsx")
def dashboard_jsx():
    jsx_file = FRONTEND_DIR / "Dashboard.jsx"
    if jsx_file.exists():
        return Response(jsx_file.read_text(), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/TopCongressBuysWidget.jsx")
def congress_widget_jsx():
    jsx_file = FRONTEND_DIR / "TopCongressBuysWidget.jsx"
    if jsx_file.exists():
        return Response(jsx_file.read_text(), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/TopCongressBuysWidget.css")
def congress_widget_css():
    css_file = FRONTEND_DIR / "TopCongressBuysWidget.css"
    if css_file.exists():
        return Response(css_file.read_text(), media_type="text/css")
    raise HTTPException(status_code=404, detail="Not Found")

# Serve contextual help JS used by the simple HTML pages
@app.get("/help.js")
def help_js():
    js_file = FRONTEND_DIR / "help.js"
    if js_file.exists():
        return Response(js_file.read_text(), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not Found")

# Serve the project README for display on the GitHub page
@app.get("/readme")
def get_readme():
    readme_file = Path(__file__).resolve().parent / "README.md"
    if readme_file.exists():
        return Response(readme_file.read_text(), media_type="text/plain")
    raise HTTPException(status_code=404, detail="Not Found")



# Serve simple static HTML pages for the frontend
@app.get("/{page_name}", response_class=HTMLResponse)
def serve_page(page_name: str):
    """Return one of the bundled frontend HTML pages."""
    allowed_pages = {"index.html", "login.html", "account.html", "tickers.html", "signals.html", "journal.html", "backtests.html", "admin.html", "help.html", "github.html"}
    if page_name in allowed_pages:
        html_file = FRONTEND_DIR / page_name
        if html_file.exists():
            # Explicitly read using UTF-8 to avoid locale dependent decoding
            return html_file.read_text(encoding="utf-8")
    raise HTTPException(status_code=404, detail="Not Found")


# Fallback for SPA routes when React build is present
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if REACT_BUILD_DIR.is_dir():
        index_file = REACT_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not Found")
