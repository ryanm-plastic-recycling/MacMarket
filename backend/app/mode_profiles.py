"""Trading mode profiles for signals generation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ModeProfile:
    name: str
    tf: List[str]
    entry_logic: Dict[str, float]
    indicators: Dict[str, float]


MODE_PROFILES: Dict[str, ModeProfile] = {
    "day": ModeProfile(
        name="Day",
        tf=["5m", "15m"],
        entry_logic={"rsi_threshold_long": 55, "adx_min": 20},
        indicators={"use_stoch_rsi": True, "use_vwap": True, "ema_fast": 20, "ema_slow": 50},
    ),
    "swing": ModeProfile(
        name="Swing",
        tf=["1h", "1d"],
        entry_logic={"rsi_threshold_long": 55, "adx_min": 25},
        indicators={"ema_fast": 50, "ema_slow": 200, "atr_mult_stop": 2.0},
    ),
    "position": ModeProfile(
        name="Position",
        tf=["1d", "1w"],
        entry_logic={"rsi_threshold_long": 55, "adx_min": 20},
        indicators={"ema_fast": 50, "ema_slow": 200, "atr_mult_stop": 2.5},
    ),
    "crypto": ModeProfile(
        name="Crypto",
        tf=["4h", "1d"],
        entry_logic={"rsi_threshold_long": 55, "adx_min": 23},
        indicators={"ema_fast": 50, "ema_slow": 200, "atr_mult_stop": 2.0, "weekend_gaps": False},
    ),
}

WATCHLIST_SYMBOLS: List[str] = [
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "XLK",
    "XLF",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "TSLA",
    "META",
    "ES",
    "NQ",
    "GC",
    "CL",
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
]
