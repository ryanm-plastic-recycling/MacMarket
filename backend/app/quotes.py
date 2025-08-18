import os
import time
from typing import Dict, List, Tuple, Optional

import yfinance as yf
import pandas as pd

# Simple TTL cache (symbol -> (expires_epoch, price_float))
_CACHE: Dict[str, Tuple[float, float]] = {}
_TTL = int(os.getenv("QUOTE_TTL_SECONDS", "60"))

def _now() -> float:
    return time.time()

def _get_cached(sym: str) -> Optional[float]:
    v = _CACHE.get(sym)
    if not v:
        return None
    exp, price = v
    if _now() <= exp:
        return price
    try:
        del _CACHE[sym]
    except KeyError:
        pass
    return None

def _set_cached(sym: str, price: float) -> None:
    _CACHE[sym] = (_now() + _TTL, float(price))

def _last_valid_close(series: pd.Series) -> Optional[float]:
    if series is None or series.empty:
        return None
    s = series.dropna()
    if s.empty:
        return None
    return float(s.iloc[-1])

def fetch_latest_prices(symbols: List[str]) -> Dict[str, Optional[float]]:
    """Return latest (most recent valid) daily close for each symbol.
    Uses cache per symbol; batch-fetches missing ones via yfinance once.
    """
    symbols = [s.strip().upper() for s in symbols if s and s.strip()]
    out: Dict[str, Optional[float]] = {}
    need: List[str] = []

    for s in symbols:
        cached = _get_cached(s)
        if cached is not None:
            out[s] = cached
        else:
            need.append(s)

    if need:
        df = yf.download(
            need,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
        for s in need:
            price: Optional[float] = None
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    if (s, "Close") in df.columns:
                        series = df[(s, "Close")]
                    elif (s, "Adj Close") in df.columns:
                        series = df[(s, "Adj Close")]
                    else:
                        series = None
                else:
                    if "Close" in df.columns:
                        series = df["Close"]
                    elif "Adj Close" in df.columns:
                        series = df["Adj Close"]
                    else:
                        series = None
                price = _last_valid_close(series)
            except Exception:
                price = None
            out[s] = price
            if price is not None:
                _set_cached(s, price)
    return out

def fetch_latest_price(symbol: str) -> Optional[float]:
    return fetch_latest_prices([symbol]).get(symbol)
