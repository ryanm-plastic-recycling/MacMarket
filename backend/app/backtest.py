"""Very small backtesting utilities."""

import pandas as pd
import numpy as np
import yfinance as yf


def _performance_metrics(df: pd.DataFrame) -> dict:
    df = df.dropna(subset=["strategy_return"])
    total_return = df["equity"].iloc[-1] - 1
    days = (df.index[-1] - df.index[0]).days
    years = days / 365.25 if days else 1
    cagr = df["equity"].iloc[-1] ** (1 / years) - 1
    roll_max = df["equity"].cummax()
    drawdown = df["equity"] / roll_max - 1
    max_dd = drawdown.min()
    sharpe = (
        np.sqrt(252) * df["strategy_return"].mean() / df["strategy_return"].std()
        if df["strategy_return"].std() != 0
        else 0
    )
    return {
        "total_return": round(float(total_return), 4),
        "cagr": round(float(cagr), 4),
        "max_drawdown": round(float(max_dd), 4),
        "sharpe": round(float(sharpe), 2),
    }


def sma_crossover_backtest(symbol: str, start: str = "2023-01-01", end: str | None = None) -> dict:
    """Run a simple SMA crossover backtest and return trades and metrics."""
    df = yf.download(symbol, start=start, end=end)
    if df.empty:
        return {"trades": [], "metrics": {}, "equity": []}

    df["sma_20"] = df["Close"].rolling(20).mean()
    df["sma_50"] = df["Close"].rolling(50).mean()
    df["signal"] = 0
    df.loc[df["sma_20"] > df["sma_50"], "signal"] = 1
    df.loc[df["sma_20"] < df["sma_50"], "signal"] = -1
    df["position"] = df["signal"].shift(1).fillna(0)
    df["ret"] = df["Close"].pct_change().fillna(0)
    df["strategy_return"] = df["position"] * df["ret"]
    df["equity"] = (1 + df["strategy_return"]).cumprod()

    trades = []
    prev = 0
    for date, row in df.iterrows():
        if row["signal"] != prev and row["signal"] != 0:
            action = "buy" if row["signal"] == 1 else "sell"
            trades.append({"date": date.strftime("%Y-%m-%d"), "action": action, "price": float(row["Close"])})
        prev = row["signal"]

    metrics = _performance_metrics(df)
    equity = [
        {"date": d.strftime("%Y-%m-%d"), "value": float(v)} for d, v in zip(df.index, df["equity"])
    ]
    return {"trades": trades, "metrics": metrics, "equity": equity}
