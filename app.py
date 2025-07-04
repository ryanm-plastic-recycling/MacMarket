from fastapi import FastAPI, HTTPException, Depends
from backend.app.database import connect_to_db, SessionLocal, engine
from sqlalchemy.orm import Session
from backend.app import models, crud, schemas

from fastapi.responses import HTMLResponse
from pathlib import Path
import yfinance as yf
import requests

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# Directory containing the HTML frontend files
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


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
        conn = connect_to_db()
        conn.close()
        return {"status": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the main frontend page."""
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
            data.append({"symbol": symbol, "price": price, "change_percent": change})
        except Exception:
            data.append({"symbol": symbol, "price": None, "change_percent": None})
    return {"data": data}


@app.get("/api/news")
def news():
    """Fetch finance-related news articles from multiple sources."""
    articles = []
    try:
        res = requests.get("https://hn.algolia.com/api/v1/search", params={"query": "market", "tags": "story"})
        articles.extend([
            {"title": h.get("title"), "url": h.get("url")}
            for h in res.json().get("hits", [])[:5]
        ])
    except Exception:
        pass
    def add_rss(url):
        try:
            r = requests.get(url)
            from xml.etree import ElementTree
            root = ElementTree.fromstring(r.content)
            for item in root.findall('.//item')[:5]:
                title = item.findtext('title')
                link = item.findtext('link')
                if title and link:
                    articles.append({"title": title, "url": link})
        except Exception:
            pass
    add_rss('https://feeds.foxnews.com/foxnews/business')
    add_rss('https://www.bloomberg.com/feed/podcast/etf-report.xml')
    add_rss('https://feeds.foxbusiness.com/foxbusiness/markets')
    return {"articles": articles}


@app.post("/api/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    """Create or fetch a user by username and password."""
    try:
        db_user = crud.get_or_create_user(db, user.username, user.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": db_user.id, "username": db_user.username}


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


# Serve simple static HTML pages for the frontend
@app.get("/{page_name}", response_class=HTMLResponse)
def serve_page(page_name: str):
    """Return one of the bundled frontend HTML pages."""
    allowed_pages = {"index.html", "login.html", "account.html", "tickers.html"}
    if page_name in allowed_pages:
        html_file = FRONTEND_DIR / page_name
        if html_file.exists():
            return html_file.read_text()
    raise HTTPException(status_code=404, detail="Not Found")
