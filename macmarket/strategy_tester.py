import os
import pandas as pd
import datetime
import requests
import yfinance as yf
from pathlib import Path
from .paper_trader import PaperTrader
from backend.app.backtest import _performance_metrics

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _load_config() -> dict:
    if CONFIG_PATH.is_file():
        try:
            import yaml
            with open(CONFIG_PATH) as f:
                data = yaml.safe_load(f) or {}
            return data
        except Exception:
            return {}
    return {}


class CongressLongShortTester:
    """Backtester for the Congress Long-Short strategy."""

    def __init__(self) -> None:
        cfg = _load_config()
        strat_cfg = cfg.get("strategy_tester", {})
        self.api_token = cfg.get("quiver_api_token") or os.getenv("QUIVER_API_KEY")
        self.initial_capital = strat_cfg.get("initial_capital", 100000.0)
        self.lookback_days = strat_cfg.get("lookback_days", 7)
        self.rebalance_freq = strat_cfg.get("rebalance_frequency_days", 7)
        self.output_csv = Path("data/backtests/congress_long_short.csv")
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)

    def _fetch_trades(self, start: datetime.date, end: datetime.date) -> pd.DataFrame:
        headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        url = "https://api.quiverquant.com/beta/live/congresstrading"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("data", data)
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=["date", "symbol", "size", "signal"])
        sym_col = next((c for c in ["Ticker", "ticker", "Symbol", "symbol"] if c in df.columns), None)
        date_col = next((c for c in ["Date", "TransactionDate", "TradeDate", "date"] if c in df.columns), None)
        action_col = next((c for c in ["Transaction", "Action", "Type"] if c in df.columns), None)
        size_col = next((c for c in ["Range", "Size", "amount", "Amount"] if c in df.columns), None)
        df = df.rename(columns={sym_col: "symbol", date_col: "date", action_col: "action", size_col: "size"})
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["signal"] = df["action"].str.contains("buy", case=False).astype(int)
        df.loc[df["action"].str.contains("sell|sale", case=False), "signal"] = -1
        df["size"] = df["size"].apply(self._parse_size)
        df = df[(df["date"] >= start) & (df["date"] <= end)]
        return df[["date", "symbol", "size", "signal"]]

    @staticmethod
    def _parse_size(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            parts = val.replace("$", "").replace(",", "").split("-")
            nums = []
            for p in parts:
                try:
                    nums.append(float(p))
                except ValueError:
                    continue
            if nums:
                return sum(nums) / len(nums)
        return 1.0

    def _weights_from_trades(self, trades: pd.DataFrame) -> dict[str, float]:
        if trades.empty:
            return {}
        longs = trades[trades["signal"] == 1].groupby("symbol")["size"].sum()
        shorts = trades[trades["signal"] == -1].groupby("symbol")["size"].sum()
        total = longs.sum() + shorts.sum()
        weights: dict[str, float] = {}
        if total == 0:
            return weights
        for sym, val in longs.items():
            weights[sym] = weights.get(sym, 0.0) + val / total
        for sym, val in shorts.items():
            weights[sym] = weights.get(sym, 0.0) - val / total
        return weights

    def _price_series(self, symbols: list[str], start: datetime.date, end: datetime.date) -> dict[str, pd.Series]:
        data = {}
        for sym in symbols:
            try:
                df = yf.download(sym, start=start, end=end + datetime.timedelta(days=1), progress=False)
                if not df.empty:
                    data[sym] = df["Close"].ffill()
            except Exception:
                pass
        return data

    @staticmethod
    def _nearest(series: pd.Series, date: datetime.date) -> float | None:
        if series.empty:
            return None
        dt = pd.to_datetime(date)
        if dt in series.index:
            return float(series.loc[dt])
        before = series.loc[:dt]
        if not before.empty:
            return float(before.iloc[-1])
        return float(series.iloc[0])

    def run_backtest(self) -> dict:
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=self.rebalance_freq + self.lookback_days)
        trades = self._fetch_trades(start_date - datetime.timedelta(days=self.lookback_days), today)
        symbols = sorted(trades["symbol"].unique())
        prices = self._price_series(symbols, start_date, today)
        rebalance_date = start_date
        pt = PaperTrader(self.initial_capital)
        equity_curve = []
        while rebalance_date < today:
            lb_start = rebalance_date - datetime.timedelta(days=self.lookback_days)
            subset = trades[(trades["date"] > lb_start) & (trades["date"] <= rebalance_date)]
            weights = self._weights_from_trades(subset)
            price_map = {s: self._nearest(prices.get(s, pd.Series(dtype=float)), rebalance_date) for s in weights}
            pt.target_weights(weights, price_map, rebalance_date)
            equity = pt.portfolio_value({s: self._nearest(prices.get(s, pd.Series(dtype=float)), rebalance_date) for s in pt.positions})
            equity_curve.append({"date": rebalance_date, "equity": equity})
            rebalance_date += datetime.timedelta(days=self.rebalance_freq)
        final_prices = {s: self._nearest(prices.get(s, pd.Series(dtype=float)), today) for s in pt.positions}
        final_equity = pt.finalize(final_prices, today)
        equity_curve.append({"date": today, "equity": final_equity})
        hist_df = pt.history_df()
        hist_df.to_csv(self.output_csv, index=False)
        eq_df = pd.DataFrame(equity_curve).set_index("date")
        eq_df["strategy_return"] = eq_df["equity"].pct_change().fillna(0)
        metrics = _performance_metrics(eq_df)
        return metrics
