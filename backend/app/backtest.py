"""Very small backtesting utilities."""

import pandas as pd
import yfinance as yf


def sma_crossover_backtest(symbol: str, start: str = "2023-01-01") -> dict:
    """Run a simple SMA crossover backtest and return the trade log."""
    df = yf.download(symbol, start=start)
    if df.empty:
        return {"trades": []}
    df["sma_20"] = df["Close"].rolling(20).mean()
    df["sma_50"] = df["Close"].rolling(50).mean()
    position = 0
    trades = []
    for date, row in df.iterrows():
        if row["sma_20"] > row["sma_50"] and position <= 0:
            position = 1
            trades.append({"date": date.strftime("%Y-%m-%d"), "action": "buy", "price": float(row["Close"])})
        elif row["sma_20"] < row["sma_50"] and position >= 0:
            position = -1
            trades.append({"date": date.strftime("%Y-%m-%d"), "action": "sell", "price": float(row["Close"])})
    return {"trades": trades}
