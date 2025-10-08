"""Simple datafeed wrapper using yfinance."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import yfinance as yf

INTERVAL_MAP = {
    "5m": ("5m", "5d"),
    "15m": ("15m", "1mo"),
    "1h": ("60m", "3mo"),
    "4h": ("60m", "6mo"),
    "1d": ("1d", "1y"),
    "1w": ("1wk", "5y"),
}


def get_price_history(symbol: str, timeframe: str) -> pd.DataFrame:
    interval, period = INTERVAL_MAP.get(timeframe, ("1d", "6mo"))
    data = yf.download(symbol, interval=interval, period=period, auto_adjust=False, progress=False)
    if data.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    data = data.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    data.index = pd.to_datetime(data.index)
    data = data.reset_index().rename(columns={"index": "time", "Date": "time"})
    data["time"] = data["time"].dt.tz_localize(None)
    return data
