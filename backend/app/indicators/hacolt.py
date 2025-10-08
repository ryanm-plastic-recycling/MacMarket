"""HACOLT state machine derived from the HACO oscillator."""
from __future__ import annotations

import pandas as pd

from .haco import haco


def hacolt_state(df: pd.DataFrame, length: int = 10, smooth: int = 5) -> pd.Series:
    osc = haco(df, length=length, smooth=smooth)
    if osc.empty:
        return osc
    slope = osc.diff().fillna(0)
    state = pd.Series(index=osc.index, dtype=float)
    for i in range(len(osc)):
        value = osc.iloc[i]
        slope_now = slope.iloc[i]
        if value > 60 and slope_now >= 0:
            state.iloc[i] = 100
        elif value < -60 and slope_now <= 0:
            state.iloc[i] = 0
        else:
            state.iloc[i] = 50
    return state
