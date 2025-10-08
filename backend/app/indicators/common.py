"""Indicator utilities for HACO/HACOLT driven workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np
import pandas as pd


@dataclass
class HeikinAshi:
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series


def ensure_series(values: Iterable[float]) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(float)
    return pd.Series(list(values), dtype=float)


def ema(series: Iterable[float], length: int) -> pd.Series:
    s = ensure_series(series)
    if len(s) == 0:
        return s
    return s.ewm(span=length, adjust=False).mean()


def rsi(series: Iterable[float], length: int = 14) -> pd.Series:
    s = ensure_series(series)
    if len(s) == 0:
        return s
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(span=length, adjust=False).mean()
    roll_down = down.ewm(span=length, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return rsi_series.fillna(0)


def atr(high: Iterable[float], low: Iterable[float], close: Iterable[float], length: int = 14) -> pd.Series:
    h = ensure_series(high)
    l = ensure_series(low)
    c = ensure_series(close)
    if len(h) == 0:
        return h
    prev_close = c.shift(1)
    tr = pd.concat(
        [
            (h - l),
            (h - prev_close).abs(),
            (l - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=length, min_periods=1).mean()


def adx(high: Iterable[float], low: Iterable[float], close: Iterable[float], length: int = 14) -> pd.Series:
    h = ensure_series(high)
    l = ensure_series(low)
    c = ensure_series(close)
    if len(h) == 0:
        return h
    tr = atr(h, l, c, length)
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100 * ema(plus_dm, length) / tr.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, length) / tr.replace(0, np.nan)
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    return ema(dx.fillna(0), length)


def obv(close: Iterable[float], volume: Iterable[float]) -> pd.Series:
    c = ensure_series(close)
    v = ensure_series(volume)
    if len(c) == 0:
        return c
    direction = np.sign(c.diff().fillna(0))
    return (direction * v).cumsum()


def vfi(close: Iterable[float], volume: Iterable[float], length: int = 30) -> pd.Series:
    c = ensure_series(close)
    v = ensure_series(volume)
    if len(c) == 0:
        return c
    typical_price = (c + c.shift(1)) / 2
    typical_price.iloc[0] = c.iloc[0]
    volatility = atr(c, c, c, length).replace(0, np.nan)
    delta = c.diff()
    vf = np.where(delta > volatility, v, np.where(delta < -volatility, -v, 0))
    return pd.Series(vf, index=c.index).rolling(length, min_periods=1).mean()


def macd(series: Iterable[float], fast: int = 12, slow: int = 26, signal_len: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    s = ensure_series(series)
    if len(s) == 0:
        empty = pd.Series(dtype=float)
        return empty, empty, empty
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    macd_line = ema_fast - ema_slow
    signal = ema(macd_line, signal_len)
    hist = macd_line - signal
    return macd_line, signal, hist


def supertrend(high: Iterable[float], low: Iterable[float], close: Iterable[float], length: int = 10, multiplier: float = 3.0) -> pd.Series:
    h = ensure_series(high)
    l = ensure_series(low)
    c = ensure_series(close)
    if len(h) == 0:
        return h
    atr_series = atr(h, l, c, length)
    hl2 = (h + l) / 2
    upper_band = hl2 + multiplier * atr_series
    lower_band = hl2 - multiplier * atr_series

    trend = pd.Series(index=c.index, dtype=float)
    direction = pd.Series(1, index=c.index, dtype=int)

    for i in range(len(c)):
        if i == 0:
            trend.iloc[i] = lower_band.iloc[i]
            continue
        if c.iloc[i] > trend.iloc[i - 1]:
            direction.iloc[i] = 1
        elif c.iloc[i] < trend.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            trend.iloc[i] = max(lower_band.iloc[i], trend.iloc[i - 1])
        else:
            trend.iloc[i] = min(upper_band.iloc[i], trend.iloc[i - 1])
    return trend.ffill()


def heikin_ashi(df: pd.DataFrame) -> HeikinAshi:
    if df.empty:
        empty = pd.Series(dtype=float, index=df.index)
        return HeikinAshi(empty, empty, empty, empty)
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2
    ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)
    return HeikinAshi(ha_open, ha_high, ha_low, ha_close)
