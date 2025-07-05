"""Generate trading signals from various data sources."""

from __future__ import annotations

import os
import requests
import pandas as pd
import yfinance as yf

try:
    import openai  # optional
except Exception:  # pragma: no cover - optional dep
    openai = None

POSITIVE_WORDS = {"gain", "growth", "bull", "optimistic", "up"}
NEGATIVE_WORDS = {"loss", "drop", "bear", "pessimistic", "down"}


def news_sentiment_signal(symbol: str) -> dict:
    """Return a simple sentiment score based on recent headlines."""
    try:
        res = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": symbol, "tags": "story"},
            timeout=5,
        )
        articles = [h.get("title", "") for h in res.json().get("hits", [])[:5]]
    except Exception:
        articles = []
    score = 0
    for title in articles:
        words = {w.strip('.,').lower() for w in title.split()}
        score += len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)
    return {"type": "news_sentiment", "symbol": symbol, "score": score}


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
