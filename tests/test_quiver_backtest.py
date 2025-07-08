import pandas as pd
import scripts.backtest_signals as bs

class DummyResp:
    def __init__(self, data):
        self._data = data
        self.ok = True
    def json(self):
        return self._data
    def raise_for_status(self):
        pass

def test_load_quiver_trades_whales(monkeypatch):
    data = [{"Ticker": "AAPL", "Date": "2024-01-01", "Action": "Buy"}]
    monkeypatch.setattr(bs.requests, "get", lambda *a, **k: DummyResp(data))
    df = bs.load_quiver_trades("AAPL", "2023-12-01", "2024-02-01", "whales", limit=5)
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["signal"] == 1


def test_load_quiver_trades_political(monkeypatch):
    data = [{"Ticker": "AAPL", "TransactionDate": "2024-03-01", "Transaction": "Sale"}]
    monkeypatch.setattr(bs.requests, "get", lambda *a, **k: DummyResp(data))
    df = bs.load_quiver_trades("AAPL", "2024-02-01", "2024-04-01", "political", limit=5)
    assert not df.empty
    assert df.iloc[0]["signal"] == -1
