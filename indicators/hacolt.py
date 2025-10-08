"""HACO Trend helpers migrated from the Codex prototype."""

from __future__ import annotations

from typing import Iterable, List

from .common import ema, heikin_ashi


def compute_trend(candles: Iterable[dict[str, float]], period: int = 34) -> List[float]:
    """Return a zero-lag trend estimate using a Heikin-Ashi projection."""

    ha = heikin_ashi(candles)
    closes = [c["c"] for c in ha]
    tema1 = ema(closes, period)
    tema2 = ema(tema1, period)
    tema3 = ema(tema2, period)
    # classic zero-lag triple EMA projection
    return [3 * a - 3 * b + c for a, b, c in zip(tema1, tema2, tema3)]


def trend_direction(trend: List[float]) -> str:
    """Return ``up``/``down``/``flat`` depending on the last two readings."""

    if len(trend) < 2:
        return "flat"
    if trend[-1] > trend[-2]:
        return "up"
    if trend[-1] < trend[-2]:
        return "down"
    return "flat"


__all__ = ["compute_trend", "trend_direction"]
