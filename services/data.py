from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict

import yfinance as yf
from datetime import datetime, timezone


def _to_time(v):
    s = str(v).strip() if v is not None else ""
    # epoch seconds or ms
    if s.replace('.', '', 1).isdigit():
        x = float(s)
        return int(x / 1000) if x > 1e12 else int(x)
    # ISO or YYYY-MM-DD
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        dt = datetime.strptime(s, '%Y-%m-%d')
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


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
            for rec in reader:
                try:
                    key_map = {
                        "o": "open", "h": "high", "l": "low", "c": "close",
                        "O": "open", "H": "high", "L": "low", "C": "close",
                        "Date": "date", "timestamp": "time", "Timestamp": "time"
                    }
                    rec2 = {key_map.get(k, k): v for k, v in rec.items()}
                    row = {
                        "time": _to_time(rec2.get("time") or rec2.get("date")),
                        "o": float(rec2.get("o") or rec2.get("open")),
                        "h": float(rec2.get("h") or rec2.get("high")),
                        "l": float(rec2.get("l") or rec2.get("low")),
                        "c": float(rec2.get("c") or rec2.get("close")),
                    }
                    candles.append(row)
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
                    candles.append({
                        "time": _to_time(ts),
                        "o": float(row["Open"]),
                        "h": float(row["High"]),
                        "l": float(row["Low"]),
                        "c": float(row["Close"]),
                    })
        except Exception:
            # If the remote fetch fails we simply return whatever we had
            pass

    return candles[-lookback:]
