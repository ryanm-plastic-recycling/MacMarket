from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from backend.app.indicators.hacolt import hacolt_state
from backend.app.mode_profiles import MODE_PROFILES
from backend.app.services import signals_engine


def _sample_df(size: int = 60, start: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    rows = []
    now = datetime(2023, 1, 1)
    price = start
    for i in range(size):
        rows.append(
            {
                "time": now + timedelta(days=i),
                "open": price - 0.3,
                "high": price + 0.6,
                "low": price - 0.8,
                "close": price,
                "volume": 1_000_000 + i * 10_000,
            }
        )
        price += step
    return pd.DataFrame(rows)


def test_trend_panel_bullish_alignment():
    df = _sample_df()
    profile = MODE_PROFILES["swing"]
    panel = signals_engine._trend_panel(df, profile)
    assert panel.status == "PASS"
    assert panel.score == 100


def test_momentum_panel_mapping(monkeypatch):
    df = _sample_df(size=5)
    profile = MODE_PROFILES["swing"]

    fake_rsi = pd.Series([40, 50, 55, 60, 65], index=df.index)
    monkeypatch.setattr(signals_engine, "rsi", lambda series, length=14: fake_rsi)

    panel = signals_engine._momentum_panel(df, profile)
    assert panel.status == "PASS"
    assert 60 <= panel.score <= 100


def test_volatility_panel_threshold(monkeypatch):
    df = _sample_df(size=5)
    profile = MODE_PROFILES["swing"]
    fake_adx = pd.Series([10, 15, 22, 27, 35], index=df.index)
    monkeypatch.setattr(signals_engine, "adx", lambda h, l, c, length=14: fake_adx)

    panel = signals_engine._volatility_panel(df, profile)
    assert panel.status == "PASS"
    assert panel.score == 80


def test_volume_panel_slope_positive(monkeypatch):
    df = _sample_df(size=10)
    fake_obv = pd.Series(range(0, 1_000_000, 100_000), index=df.index)
    monkeypatch.setattr(signals_engine, "obv", lambda close, volume: fake_obv)

    panel = signals_engine._volume_panel(df)
    assert panel.status == "PASS"
    assert panel.score >= 60


def test_hacolt_transitions():
    df = _sample_df(size=30, step=1)
    states = hacolt_state(df)
    assert set(states.unique()).issubset({0.0, 50.0, 100.0})
    assert states.iloc[-1] in {50.0, 100.0}
