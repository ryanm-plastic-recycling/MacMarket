import pandas as pd

from backend.app import signals


def test_compute_signals_structure(monkeypatch):
    def fake_download(*args, **kwargs):
        # returning empty frame triggers deterministic fallback
        return pd.DataFrame()

    monkeypatch.setattr("backend.app.signals.yf.download", fake_download)

    payload = signals.compute_signals("SPY", mode="swing")

    assert payload["symbol"] == "SPY"
    assert payload["mode"] == "swing"
    assert set(payload.keys()) >= {
        "panels",
        "readiness",
        "entries",
        "exits",
        "chart",
        "advanced_tabs",
        "available_modes",
        "watchlist",
    }
    assert len(payload["panels"]) == 4
    assert payload["readiness"]["score"] >= 0

    candles = payload["chart"]["candles"]
    assert candles, "Expected fallback candles to be present"
    assert isinstance(candles[0]["time"], int)

    modes = payload["available_modes"]
    assert "swing" in modes
    assert all(mode.islower() for mode in modes)


def test_compute_signals_unknown_mode(monkeypatch):
    monkeypatch.setattr("backend.app.signals.yf.download", lambda *a, **k: pd.DataFrame())

    payload = signals.compute_signals("QQQ", mode="unknown")

    assert payload["mode"] == "swing"
    assert payload["symbol"] == "QQQ"
