"""Generate trading signals from various data sources."""

from __future__ import annotations

import os
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
        exit_price = None
        if price:
            exit_price = price * (1.05 if action == "buy" else 0.95)
            exit_price = format_price(exit_price)
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
        if exit_price:
            exit_str = f"{exit_price:.5f}" if abs(exit_price) < 1 else f"{exit_price:.2f}"
            reason += f" Exit is {exit_str} based on 5% target"
        recs.append({
            "symbol": sym,
            "action": action,
            "exit": exit_price,
            "probability": probability,
            "reason": reason,
        })
    recs.sort(key=lambda x: x["probability"], reverse=True)
    return recs[:3]
