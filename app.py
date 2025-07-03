from fastapi import FastAPI, HTTPException
from backend.app.database import connect_to_db

from fastapi.responses import HTMLResponse
from pathlib import Path
import yfinance as yf
import requests

app = FastAPI()


@app.get("/health")
def health():
    """Simple health check."""
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    """Check database connectivity."""
    try:
        conn = connect_to_db()
        conn.close()
        return {"status": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the frontend page."""
    html_path = Path(__file__).resolve().parent / "frontend" / "index.html"
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
            data.append({"symbol": symbol, "price": price, "change_percent": change})
        except Exception:
            data.append({"symbol": symbol, "price": None, "change_percent": None})
    return {"data": data}


@app.get("/api/news")
def news():
    """Fetch simple finance-related news articles."""
    try:
        res = requests.get("https://hn.algolia.com/api/v1/search", params={"query": "market", "tags": "story"})
        articles = [
            {"title": h.get("title"), "url": h.get("url")}
            for h in res.json().get("hits", [])[:10]
        ]
    except Exception:
        articles = []
    return {"articles": articles}
