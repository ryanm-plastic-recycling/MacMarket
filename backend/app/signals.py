"""Generate trading signals from various data sources."""

from __future__ import annotations

import os
import logging
import datetime
import requests
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    import openai  # optional
except Exception:  # pragma: no cover - optional dep
    openai = None

POSITIVE_WORDS = {"gain", "growth", "bull", "optimistic", "up"}
NEGATIVE_WORDS = {"loss", "drop", "bear", "pessimistic", "down"}

# Exit strategy configuration
EXIT_PROFIT_TARGET_PCT = 0.05  # 5% profit target
EXIT_STOP_LOSS_PCT = 0.02     # 2% stop-loss
EXIT_MAX_HOLD_DAYS = 30       # time-based exit after 30 trading days


def format_price(value: float | None) -> float | None:
    """Return value rounded to 5 decimals when under $1, otherwise 2 decimals."""
    if value is None:
        return None
    return round(value, 5) if abs(value) < 1 else round(value, 2)


def get_risk_factors(symbols: list[str]) -> dict:
    """Return a mapping of symbol to Quiver risk score."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/riskfactors",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                scores = {}
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym:
                        score = item.get("RiskScore") or item.get("Score")
                        try:
                            scores[sym] = float(score)
                        except (TypeError, ValueError):
                            pass
                return scores
    except Exception:
        pass
    return {}


def get_whale_moves(limit: int = 5) -> list[dict]:
    """Return recent whale moves from Quiver."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/whalemoves",
            headers=headers,
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return data[:limit]
    except Exception:
        pass
    return []


async def fetch_unusual_whales(limit: int = 5) -> list[dict]:
    """Fetch latest unusual whale alerts."""
    import httpx

    key = os.getenv("WHALES_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.unusualwhales.com/alerts", headers=headers
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    data = data.get("results", data)
                if isinstance(data, list):
                    return data[:limit]
    except Exception:
        pass
    return []


def get_political_moves(symbols: list[str]) -> dict:
    """Return counts of recent congressional trades for each symbol."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/congresstrading",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            counts: dict[str, int] = {}
            if isinstance(data, list):
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym and sym in symbols:
                        counts[sym] = counts.get(sym, 0) + 1
            return counts
    except Exception:
        pass
    return {}


def get_lobby_disclosures(symbols: list[str]) -> dict:
    """Return counts of recent lobbying disclosures for each symbol."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/lobbying",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            counts: dict[str, int] = {}
            if isinstance(data, list):
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym and sym in symbols:
                        counts[sym] = counts.get(sym, 0) + 1
            return counts
    except Exception:
        pass
    return {}


def news_sentiment_signal(symbol: str) -> dict:
    """Return a sentiment score based on recent financial news headlines."""
    params = {"q": symbol, "pageSize": 5}
    key = os.getenv("NEWSAPI_KEY")
    if key:
        params["apiKey"] = key
    articles: list[str] = []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params=params,
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            articles = [a.get("title", "") for a in data.get("articles", [])[:5]]
    except Exception:
        articles = []
    analyzer = SentimentIntensityAnalyzer()
    score = 0.0
    for title in articles:
        score += analyzer.polarity_scores(title)["compound"]
    return {
        "type": "news_sentiment",
        "symbol": symbol,
        "score": round(score, 2),
    }


def technical_indicator_signal(symbol: str) -> dict:
    """Generate a simple moving-average crossover signal."""
    data = yf.download(symbol, period="3mo", interval="1d")
    if data.empty:
        return {"type": "technical", "symbol": symbol, "signal": "none"}
    data["ma_short"] = data["Close"].rolling(20).mean()
    data["ma_long"] = data["Close"].rolling(50).mean()
    if data["ma_short"].iloc[-1] > data["ma_long"].iloc[-1]:
        signal = "bullish"
    else:
        signal = "bearish"
    return {"type": "technical", "symbol": symbol, "signal": signal}


def macro_llm_signal(text: str) -> dict:
    """Use an LLM to interpret macroeconomic commentary."""
    if openai and os.getenv("OPENAI_API_KEY"):
        try:  # pragma: no cover - external call
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Given the following macroeconomic summary, "
                            "respond with one word: bullish, bearish, or neutral.\n" + text
                        ),
                    }
                ],
            )
            outlook = resp.choices[0].message["content"].strip()
            return {"type": "macro_llm", "outlook": outlook}
        except Exception:
            pass
    return {"type": "macro_llm", "outlook": "unknown"}

def _current_price(symbol: str) -> float | None:
    """Return the latest price for a symbol."""
    try:
        t = yf.Ticker(symbol)
        price = t.info.get("regularMarketPrice")
        if price is None:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price is not None else None
    except Exception:
        return None


def _calculate_exit(
    symbol: str, entry_price: float, entry_date: datetime.date
) -> tuple[datetime.date, float]:
    """Return exit date and price based on fixed target, stop and time limit."""
    forward = None
    exit_date = None
    exit_price = None
    try:
        forward = yf.download(
            symbol,
            start=entry_date,
            period=f"{EXIT_MAX_HOLD_DAYS}d",
            interval="1d",
        )
        profit_target = entry_price * (1 + EXIT_PROFIT_TARGET_PCT)
        stop_loss = entry_price * (1 - EXIT_STOP_LOSS_PCT)
        for date, row in forward.iterrows():
            price = row["Close"]
            if price >= profit_target:
                exit_date, exit_price = date.date(), profit_target
                break
            if price <= stop_loss:
                exit_date, exit_price = date.date(), stop_loss
                break
        if exit_date is None and forward is not None and not forward.empty:
            last_date = forward.index[-1].date()
            exit_date = last_date
            exit_price = forward.iloc[-1]["Close"]
    except Exception as exc:
        logging.exception("Exit calculation failed for %s", symbol)
    if exit_date is None:
        exit_date = entry_date + datetime.timedelta(days=EXIT_MAX_HOLD_DAYS)
        exit_price = entry_price
    return exit_date, float(exit_price)


def _exit_levels(symbol: str, action: str, price: float) -> tuple[dict | None, str]:
    """Return low/medium/high risk exit levels and an explanation."""
    try:
        data = yf.download(symbol, period="2mo", interval="1d")
        if data.empty:
            return None, "No historical data for exits"
        high = data["High"]
        low = data["Low"]
        close = data["Close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        support = low.rolling(20).min().iloc[-1]
        resistance = high.rolling(20).max().iloc[-1]

        if action == "buy":
            exits = {
                "low": format_price(price + atr),
                "medium": format_price(price + 2 * atr),
                "high": format_price(max(resistance, price + 3 * atr)),
            }
        else:
            exits = {
                "low": format_price(price - atr),
                "medium": format_price(price - 2 * atr),
                "high": format_price(min(support, price - 3 * atr)),
            }

        reason = (
            f"ATR {atr:.2f}, support {support:.2f}, resistance {resistance:.2f}."
            " Exits adjust for risk tolerance."
        )
        return exits, reason
    except Exception:
        return None, "Exit calculation failed"


def generate_recommendations(symbols: list[str]) -> list[dict]:
    """Return simple trade recommendations based on sentiment, technicals, and risk."""
    recs = []
    risk_scores = get_risk_factors(symbols)
    political = get_political_moves(symbols)
    lobby = get_lobby_disclosures(symbols)
    for sym in symbols:
        news = news_sentiment_signal(sym)
        tech = technical_indicator_signal(sym)
        price = _current_price(sym)
        base_score = news.get("score", 0) + (1 if tech.get("signal") == "bullish" else -1)
        risk = risk_scores.get(sym, 0)
        pol = political.get(sym, 0)
        lob = lobby.get(sym, 0)
        score = base_score - risk + 0.2 * pol + 0.1 * lob
        action = "buy" if score >= 0 else "sell"
        entry_date = datetime.date.today()
        entry_price = price
        exit_date = None
        exit_price = None
        if entry_price is not None:
            exit_date, exit_price = _calculate_exit(sym, entry_price, entry_date)
        probability = round(min(0.9, 0.5 + min(abs(score) / 10, 0.4)), 2)
        parts = [
            f"News score {news.get('score')} and {tech.get('signal')} MA signal",
            f"risk {risk}"
        ]
        if pol:
            parts.append(f"{pol} political moves")
        if lob:
            parts.append(f"{lob} lobby disclosures")
        reason = " ".join(parts) + f" suggest {action}."
        recs.append({
            "symbol": sym,
            "action": action,
            "entry_date": entry_date.isoformat(),
            "entry_price": format_price(entry_price),
            "exit_date": exit_date.isoformat() if exit_date else None,
            "exit_price": format_price(exit_price),
            "probability": probability,
            "reason": reason,
        })
    recs.sort(key=lambda x: x["probability"], reverse=True)
    return recs[:3]
