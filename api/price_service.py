"""Price service utilities using yfinance."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable

import yfinance as yf
from sqlalchemy import text

from backend.app.database import SessionLocal


def ensure_prices(tickers: Iterable[str], date_from: date, date_to: date) -> None:
    tickers = list(set(tickers))
    if not tickers:
        return
    data = yf.download(tickers, start=date_from, end=date_to + timedelta(days=1), progress=False, auto_adjust=False)
    if isinstance(data, dict) or "Close" not in data:
        return
    with SessionLocal() as db:
        for idx, row in data.iterrows():
            d = idx.date()
            for ticker in tickers:
                price = row["Close"] if len(tickers) == 1 else row["Close"][ticker]
                open_p = row["Open"] if len(tickers) == 1 else row["Open"][ticker]
                db.execute(
                    text(
                        """
                        INSERT INTO price_daily (ticker, price_date, open, close)
                        VALUES (:t, :d, :o, :c)
                        ON DUPLICATE KEY UPDATE open=VALUES(open), close=VALUES(close)
                        """
                    ),
                    {"t": ticker, "d": d, "o": float(open_p), "c": float(price)},
                )
        db.commit()


def next_trading_day(d: date) -> date:
    nd = d
    while nd.weekday() >= 5:  # Saturday/Sunday
        nd += timedelta(days=1)
    return nd
