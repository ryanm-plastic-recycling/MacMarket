from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict

import yfinance as yf


def _timeframe_to_interval(timeframe: str) -> str:
    """Map simple timeframe strings to yfinance intervals."""
    tf = timeframe.lower()
    mapping = {
        "day": "1d",
        "week": "1wk",
        "month": "1mo",
    }
    if tf in mapping:
        return mapping[tf]
    if tf.isdigit():
        # treat numeric timeframe as minutes
        return f"{tf}m"
    return "1d"


def get_candles(symbol: str, timeframe: str, lookback: int) -> List[Dict[str, float]]:
    """Return candle data for ``symbol`` and ``timeframe``.

    Tries to read from ``data/{symbol}_{timeframe}.csv`` with columns
    ``time,o,h,l,c``. If the file is missing or does not contain enough rows,
    data is fetched from Yahoo Finance using :mod:`yfinance`.
    """
    fname = Path(__file__).resolve().parent.parent / "data" / f"{symbol}_{timeframe}.csv"
    candles: List[Dict[str, float]] = []
    if fname.exists():
        with fname.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    candles.append({
                        "time": row.get("time") or row.get("date"),
                        "o": float(row["o" if "o" in row else "open"]),
                        "h": float(row["h" if "h" in row else "high"]),
                        "l": float(row["l" if "l" in row else "low"]),
                        "c": float(row["c" if "c" in row else "close"]),
                    })
                except Exception:
                    continue

    if len(candles) < lookback:
        try:
            interval = _timeframe_to_interval(timeframe)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(interval=interval, period="max")
            if not hist.empty:
                hist = hist.tail(lookback).reset_index()
                candles = []
                for _, row in hist.iterrows():
                    ts = row.iloc[0]
                    if hasattr(ts, "strftime"):
                        ts = ts.strftime("%Y-%m-%d")
                    candles.append({
                        "time": ts,
                        "o": float(row["Open"]),
                        "h": float(row["High"]),
                        "l": float(row["Low"]),
                        "c": float(row["Close"]),
                    })
        except Exception:
            # If the remote fetch fails we simply return whatever we had
            pass

    return candles[-lookback:]
