import argparse
import os
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf


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
    args = parser.parse_args()

    prices = download_prices(args.symbol, args.start, args.end)
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
