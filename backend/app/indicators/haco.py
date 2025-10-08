"""HACO oscillator implementation using Heikin Ashi body momentum."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .common import heikin_ashi, ensure_series


def haco(df: pd.DataFrame, length: int = 10, smooth: int = 5) -> pd.Series:
    """Return HACO oscillator scaled -100..100."""
    if df.empty:
        return pd.Series(dtype=float, index=df.index)
    ha = heikin_ashi(df)
    body = ha.close - ha.open
    smoothed = body.rolling(length, min_periods=1).mean()
    ema_series = smoothed.ewm(span=smooth, adjust=False).mean()
    min_val = ema_series.rolling(200, min_periods=1).min()
    max_val = ema_series.rolling(200, min_periods=1).max()
    range_span = (max_val - min_val).replace(0, np.nan)
    normalized = (ema_series - min_val) / range_span
    scaled = (normalized.fillna(0) * 200) - 100
    return scaled.clip(-100, 100)


def haco_percent(df: pd.DataFrame, length: int = 10, smooth: int = 5) -> pd.Series:
    values = haco(df, length, smooth)
    return (values + 100) / 2
