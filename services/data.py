from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict


def get_candles(symbol: str, timeframe: str, lookback: int) -> List[Dict[str, float]]:
    """Return candle data for symbol/timeframe.

    Tries to read from CSV file at data/{symbol}_{timeframe}.csv with columns
    time,o,h,l,c (header optional). Returns most recent `lookback` rows.
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
    return candles[-lookback:]
