"""Core signal calculation logic for the Signals API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from ..indicators.common import (
    adx,
    atr,
    ema,
    heikin_ashi,
    macd,
    obv,
    rsi,
    supertrend,
    vfi,
)
from ..indicators.haco import haco_percent
from ..indicators.hacolt import hacolt_state
from ..mode_profiles import MODE_PROFILES, ModeProfile
from .datafeed import get_price_history


@dataclass
class PanelResult:
    id: str
    title: str
    status: str
    score: float
    reason: str


def _trend_panel(df: pd.DataFrame, profile: ModeProfile) -> PanelResult:
    ema_fast = ema(df["close"], int(profile.indicators.get("ema_fast", 50)))
    ema_slow = ema(df["close"], int(profile.indicators.get("ema_slow", 200)))
    price = df["close"].iloc[-1]
    fast = ema_fast.iloc[-1]
    slow = ema_slow.iloc[-1]
    bull = price > fast > slow
    bear = price < fast < slow
    if bull or bear:
        score = 100
        status = "PASS"
    elif fast > slow:
        score = 60
        status = "PASS"
    else:
        score = 30
        status = "FAIL"
    direction = "bullish" if price >= fast else "mixed"
    if bear:
        direction = "bearish"
    reason = f"Close {price:.2f} vs EMA{int(profile.indicators.get('ema_fast', 50))} {fast:.2f} / EMA{int(profile.indicators.get('ema_slow', 200))} {slow:.2f} ({direction})."
    return PanelResult("trend", "Trend", status, score, reason)


def _momentum_panel(df: pd.DataFrame, profile: ModeProfile) -> PanelResult:
    rsi_series = rsi(df["close"], 14)
    last_rsi = float(rsi_series.iloc[-1])
    prev_rsi = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 else last_rsi
    score = np.interp(last_rsi, (40, 70), (0, 100))
    score = float(np.clip(score, 0, 100))
    threshold = profile.entry_logic.get("rsi_threshold_long", 55)
    rising = last_rsi >= prev_rsi
    status = "PASS" if last_rsi >= threshold and rising else "FAIL"
    reason = f"RSI14={last_rsi:.1f} (prev {prev_rsi:.1f}) threshold {threshold}."
    return PanelResult("momentum", "Momentum", status, score, reason)


def _volatility_panel(df: pd.DataFrame, profile: ModeProfile) -> PanelResult:
    adx_series = adx(df["high"], df["low"], df["close"], 14)
    last_adx = float(adx_series.iloc[-1])
    if last_adx < 20:
        score = 0
    elif last_adx < 25:
        score = 50
    elif last_adx < 40:
        score = 80
    else:
        score = 100
    status = "PASS" if last_adx >= profile.entry_logic.get("adx_min", 20) else "FAIL"
    reason = f"ADX14={last_adx:.1f} vs min {profile.entry_logic.get('adx_min', 20)}."
    return PanelResult("volatility", "Volatility", status, float(score), reason)


def _volume_panel(df: pd.DataFrame) -> PanelResult:
    obv_series = obv(df["close"], df["volume"].fillna(0))
    slope_window = min(10, len(obv_series))
    if slope_window < 3:
        slope = 0.0
    else:
        y = obv_series.iloc[-slope_window:]
        x = np.arange(len(y))
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
    if slope > 0:
        score = min(100.0, 60 + slope / 1e6)
        status = "PASS"
    elif slope == 0:
        score = 40.0
        status = "FAIL"
    else:
        score = max(0.0, 40 + slope / 1e6)
        status = "FAIL"
    reason = f"OBV slope {slope:.2f} over {slope_window} bars."
    return PanelResult("volume", "Volume", status, float(score), reason)


def _stops_panel(df: pd.DataFrame, profile: ModeProfile) -> PanelResult:
    atr_mult = float(profile.indicators.get("atr_mult_stop", 2.0))
    atr_series = atr(df["high"], df["low"], df["close"], 14)
    hacolt = hacolt_state(df)
    stop = float(df["close"].iloc[-1] - atr_series.iloc[-1] * atr_mult)
    hacolt_value = int(hacolt.iloc[-1]) if len(hacolt) else 50
    reason = f"ATR(14)={atr_series.iloc[-1]:.2f}, stop={stop:.2f}, HACOLT={hacolt_value}."
    return PanelResult("stops", "Stops/Exits", "INFO", float(hacolt_value), reason)


def compute_panels(df: pd.DataFrame, profile: ModeProfile) -> List[PanelResult]:
    panels = [
        _trend_panel(df, profile),
        _momentum_panel(df, profile),
        _volatility_panel(df, profile),
        _volume_panel(df),
    ]
    panels.append(_stops_panel(df, profile))
    return panels


def readiness_score(panels: List[PanelResult]) -> float:
    actionable = [p.score for p in panels if p.id != "stops"]
    if not actionable:
        return 0.0
    return float(np.mean(actionable))


def build_chart_payload(df: pd.DataFrame) -> Dict:
    ha = heikin_ashi(df)
    haco_series = haco_percent(df)
    rsi_series = rsi(df["close"], 14)
    adx_series = adx(df["high"], df["low"], df["close"], 14)
    chart = {
        "ohlc": [
            {
                "time": row["time"].isoformat() if hasattr(row["time"], "isoformat") else str(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0) or 0),
                "ha_open": float(ha.open.iloc[i]),
                "ha_high": float(ha.high.iloc[i]),
                "ha_low": float(ha.low.iloc[i]),
                "ha_close": float(ha.close.iloc[i]),
            }
            for i, row in df.iterrows()
        ],
        "ema_fast": ema(df["close"], 50).round(4).tolist(),
        "ema_slow": ema(df["close"], 200).round(4).tolist(),
        "haco": haco_series.round(2).tolist(),
        "rsi": rsi_series.round(2).tolist(),
        "adx": adx_series.round(2).tolist(),
    }
    return chart


def build_advanced_tabs(profile: ModeProfile) -> List[Dict]:
    return [
        {
            "id": "momentum",
            "title": "Momentum Stack",
            "description": "HACO + Heikin-Ashi color + ADX confirmation",
            "indicators": ["HACO", "Heikin Ashi", "ADX"],
        },
        {
            "id": "mechanic",
            "title": "Mechanic System",
            "description": "HACO + HACOLT + SuperTrend alignment",
            "indicators": ["HACO", "HACOLT", "SuperTrend"],
        },
        {
            "id": "swing",
            "title": "Swing Confirmation",
            "description": "HACO + RSI + MACD divergence cues",
            "indicators": ["HACO", "RSI", "MACD"],
        },
        {
            "id": "trend",
            "title": "Trend Follow",
            "description": "HACO + ATR stops for trend participation",
            "indicators": ["HACO", "ATR x2"],
        },
        {
            "id": "breadth",
            "title": "Breadth/Risk",
            "description": "Cross-asset breadth: SPY, QQQ, VIX, 10Y",
            "indicators": ["SPY", "QQQ", "VIX", "TNX"],
        },
    ]


def build_entries(df: pd.DataFrame, panels: List[PanelResult]) -> List[Dict]:
    readiness = readiness_score(panels)
    if readiness < 60:
        return []
    price = float(df["close"].iloc[-1])
    return [
        {
            "time": df["time"].iloc[-1].isoformat() if hasattr(df["time"].iloc[-1], "isoformat") else str(df["time"].iloc[-1]),
            "price": price,
            "rationale": f"Readiness {readiness:.0f}/100 with trend & momentum alignment.",
        }
    ]


def build_exits(df: pd.DataFrame, profile: ModeProfile) -> Dict:
    atr_mult = float(profile.indicators.get("atr_mult_stop", 2.0))
    atr_series = atr(df["high"], df["low"], df["close"], 14)
    hacolt = hacolt_state(df)
    last_close = float(df["close"].iloc[-1])
    trail = last_close - atr_series.iloc[-1] * atr_mult
    return {
        "atr_stop": round(trail, 2),
        "hacolt_state": int(hacolt.iloc[-1]) if len(hacolt) else 50,
    }


def compute_signals(symbol: str, mode: str) -> Dict:
    mode_key = mode.lower()
    profile = MODE_PROFILES.get(mode_key, MODE_PROFILES["swing"])
    timeframe = profile.tf[0]
    df = get_price_history(symbol, timeframe)
    if df.empty:
        raise ValueError("No market data available for symbol")
    panels = compute_panels(df, profile)
    chart = build_chart_payload(df)
    entries = build_entries(df, panels)
    exits = build_exits(df, profile)
    readiness = readiness_score(panels)
    return {
        "symbol": symbol.upper(),
        "mode": mode_key,
        "timeframe": timeframe,
        "panels": [p.__dict__ for p in panels],
        "readiness": readiness,
        "entries": entries,
        "exits": exits,
        "chart": chart,
        "chart_preset": {
            "main": "heikin-ashi",
            "overlays": [
                {"type": "ema", "length": int(profile.indicators.get("ema_fast", 50)), "color": "#2ecc71"},
                {"type": "ema", "length": int(profile.indicators.get("ema_slow", 200)), "color": "#e74c3c"},
            ],
            "subpanels": [
                {"id": "haco", "title": "HACO", "type": "oscillator"},
                {"id": "rsi", "title": "RSI(14)", "type": "rsi"},
                {"id": "adx", "title": "ADX(14)", "type": "adx"},
            ],
        },
        "advanced_tabs": build_advanced_tabs(profile),
    }
