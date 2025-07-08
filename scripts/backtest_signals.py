import argparse
import os
from typing import List

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import yfinance as yf


def _parse_action(val: str) -> int:
    """Return 1 for buy, -1 for sell, 0 otherwise."""
    if not isinstance(val, str):
        return 0
    v = val.lower()
    if "buy" in v or "long" in v:
        return 1
    if "sell" in v or "short" in v or "sale" in v:
        return -1
    return 0


def load_quiver_trades(
    symbol: str, start: str, end: str, source: str, limit: int = 100
) -> pd.DataFrame:
    """Fetch trades from the QuiverQuant API."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    if source == "whales":
        url = "https://api.quiverquant.com/beta/live/whalemoves"
        params = {}
    else:
        url = "https://api.quiverquant.com/beta/live/congresstrading"
        params = {"tickers": symbol}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("data", [])
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["date", "signal"])

    sym_col = None
    for c in ["Ticker", "ticker", "Symbol", "symbol"]:
        if c in df.columns:
            sym_col = c
            break
    if sym_col:
        df = df[df[sym_col].str.upper() == symbol.upper()]

    date_col = None
    for c in [
        "Date",
        "TradeDate",
        "TransactionDate",
        "date",
        "TransDate",
    ]:
        if c in df.columns:
            date_col = c
            break
    if not date_col:
        raise ValueError("No date column found in Quiver data")
    df["date"] = pd.to_datetime(df[date_col])

    action_col = None
    for c in ["Position", "Action", "Transaction", "Type"]:
        if c in df.columns:
            action_col = c
            break
    if action_col:
        df["signal"] = df[action_col].apply(_parse_action)
    else:
        df["signal"] = 0

    df = df.sort_values("date")
    df = df[
        (df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))
    ]
    if limit:
        df = df.head(limit)
    return df[["date", "signal"]]


def download_prices(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch daily OHLCV prices for the given symbol."""
    df = yf.download(symbol, start=start, end=end, progress=False)
    if df.empty:
        raise ValueError("No price data returned")
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    df.reset_index(inplace=True)
    df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high',
                       'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_signals(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Load trading signals from API or CSV."""
    csv_path = f"data/signals_{symbol}.csv"
    if os.path.exists(csv_path):
        signals = pd.read_csv(csv_path, parse_dates=['date'])
    else:
        api_base = os.getenv('API_BASE', 'http://localhost:9500')
        url = f"{api_base}/api/signals/{symbol}"
        resp = requests.get(url, params={'start': start, 'end': end}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and 'signals' in data:
            signals = pd.DataFrame(data['signals'])
        else:
            signals = pd.DataFrame(data)
        if 'date' not in signals.columns:
            raise ValueError('Signal data must include a date column')
    signals = signals[['date', 'signal']]
    signals['date'] = pd.to_datetime(signals['date'])
    return signals


def simulate_strategy(prices: pd.DataFrame, signals: pd.DataFrame, strategy: str = 'signal') -> pd.DataFrame:
    df = prices.merge(signals, on='date', how='left')
    df['signal'] = df['signal'].ffill().fillna(0)
    if strategy == 'buy_hold':
        df['position'] = 1
    else:
        df['position'] = df['signal'].shift(1).fillna(0)
    df['open_return'] = df['open'].shift(-1) / df['open'] - 1
    df['strategy_return'] = df['position'] * df['open_return']
    df['equity'] = (1 + df['strategy_return'].fillna(0)).cumprod()
    return df


def performance_metrics(df: pd.DataFrame) -> dict:
    df = df.dropna(subset=['strategy_return'])
    total_return = df['equity'].iloc[-1] - 1
    days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
    years = days / 365.25 if days else 1
    cagr = df['equity'].iloc[-1] ** (1 / years) - 1
    roll_max = df['equity'].cummax()
    drawdown = df['equity'] / roll_max - 1
    max_dd = drawdown.min()
    sharpe = np.sqrt(252) * df['strategy_return'].mean() / df['strategy_return'].std() if df['strategy_return'].std() != 0 else 0
    return {
        'Total Return (%)': round(total_return * 100, 2),
        'CAGR (%)': round(cagr * 100, 2),
        'Max Drawdown (%)': round(max_dd * 100, 2),
        'Sharpe Ratio': round(sharpe, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Backtest trading signals')
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--strategy', choices=['signal', 'buy_hold'], default='signal', help='Backtest strategy type')
    parser.add_argument(
        '--quiver',
        choices=['whales', 'political', 'both'],
        help='Use QuiverQuant trades as signals',
    )
    parser.add_argument('--limit', type=int, default=100, help='Limit number of Quiver trades')
    args = parser.parse_args()

    prices = download_prices(args.symbol, args.start, args.end)
    if args.quiver:
        if args.quiver == 'both':
            q1 = load_quiver_trades(args.symbol, args.start, args.end, 'whales', args.limit)
            q2 = load_quiver_trades(args.symbol, args.start, args.end, 'political', args.limit)
            signals = pd.concat([q1, q2]).sort_values('date')
        else:
            signals = load_quiver_trades(args.symbol, args.start, args.end, args.quiver, args.limit)
    else:
        signals = load_signals(args.symbol, args.start, args.end)
    df = simulate_strategy(prices, signals, strategy=args.strategy)
    metrics = performance_metrics(df)

    out_csv = f"backtest_results_{args.symbol}.csv"
    df[['date', 'equity', 'signal', 'position']].to_csv(out_csv, index=False)

    plt.figure(figsize=(10, 6))
    plt.plot(df['date'], df['equity'], label='Equity')
    plt.title(f'Equity Curve - {args.symbol}')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"backtest_equity_{args.symbol}.png")

    print('\nBacktest Summary')
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print(f"\nResults CSV: {out_csv}")
    print(f"Equity Plot: backtest_equity_{args.symbol}.png")


if __name__ == '__main__':
    main()
