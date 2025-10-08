"""Common indicator utilities shared across MacMarket signal modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


def sma(values: Sequence[float], period: int) -> List[float | None]:
    """Simple moving average that mirrors the lightweight-chart behaviour.

    The helper intentionally returns ``None`` for the warmup window so callers
    can easily drop the missing values when constructing chart payloads.
    """

    if period <= 0:
        raise ValueError("period must be positive")

    acc: float = 0.0
    window: list[float] = []
    result: list[float | None] = []

    for value in values:
        window.append(value)
        acc += value
        if len(window) > period:
            acc -= window.pop(0)
        if len(window) == period:
            result.append(acc / period)
        else:
            result.append(None)
    return result


def ema(values: Sequence[float], period: int) -> List[float]:
    """Exponential moving average.

    The implementation mirrors the existing HACO calculation so that the
    migrated Codex helpers can share behaviour without pulling in an external
    dependency.
    """

    if period <= 0:
        raise ValueError("period must be positive")
    values = list(values)
    if not values:
        return []
    k = 2 / (period + 1)
    result = [values[0]]
    for price in values[1:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def heikin_ashi(candles: Iterable[dict[str, float]]) -> list[dict[str, float]]:
    """Return a Heikin-Ashi projection of the provided candles.

    The helper accepts the simplified candle dictionary used throughout the
    project (``o``/``h``/``l``/``c`` keys) and returns a list with matching
    keys so downstream code can work with the result without any conversion.
    """

    ha_candles: list[dict[str, float]] = []
    prev_open: float | None = None
    prev_close: float | None = None
    for candle in candles:
        open_ = float(candle["o"])
        high = float(candle["h"])
        low = float(candle["l"])
        close = float(candle["c"])

        ha_close = (open_ + high + low + close) / 4
        ha_open = (open_ + close) / 2 if prev_open is None else (prev_open + prev_close) / 2
        ha_high = max(high, ha_open, ha_close)
        ha_low = min(low, ha_open, ha_close)

        ha_candles.append({"o": ha_open, "h": ha_high, "l": ha_low, "c": ha_close})
        prev_open = ha_open
        prev_close = ha_close
    return ha_candles


@dataclass(slots=True)
class TrendSnapshot:
    """Light-weight structure describing the state of a trend indicator."""

    direction: str
    strength: float


def normalise_score(value: float, *, lower: float = -1.0, upper: float = 1.0) -> float:
    """Map ``value`` into the 0-100 scoring range used by the UI."""

    if lower >= upper:
        raise ValueError("lower bound must be below upper bound")
    value = max(lower, min(upper, value))
    return (value - lower) / (upper - lower) * 100


__all__ = ["TrendSnapshot", "ema", "heikin_ashi", "normalise_score", "sma"]
