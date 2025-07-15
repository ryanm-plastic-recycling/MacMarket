import pandas as pd

class PaperTrader:
    """Very simple paper trading engine for backtesting."""
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, float] = {}
        self.history: list[dict] = []

    def _record(self, date, **fields):
        rec = {"date": pd.to_datetime(date).date(), **fields}
        self.history.append(rec)

    def target_weights(self, weights: dict[str, float], prices: dict[str, float], date) -> None:
        """Adjust holdings to match the target weights at given prices."""
        equity = self.portfolio_value(prices)
        for sym, target_w in weights.items():
            price = prices.get(sym)
            if price is None or price <= 0:
                continue
            target_dollar = equity * target_w
            target_qty = target_dollar / price
            current_qty = self.positions.get(sym, 0.0)
            delta = target_qty - current_qty
            if abs(delta) < 1e-8:
                continue
            action = "buy" if delta > 0 else "sell"
            self.cash -= delta * price
            self.positions[sym] = current_qty + delta
            self._record(date, symbol=sym, action=action, quantity=abs(delta), price=float(price))
        self._record(date, equity=self.portfolio_value(prices))

    def portfolio_value(self, prices: dict[str, float]) -> float:
        value = self.cash
        for sym, qty in self.positions.items():
            price = prices.get(sym)
            if price is not None:
                value += qty * price
        return float(value)

    def finalize(self, prices: dict[str, float], date) -> float:
        """Record final equity value."""
        equity = self.portfolio_value(prices)
        self._record(date, equity=equity)
        return equity

    def history_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.history)
