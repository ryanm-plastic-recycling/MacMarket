"""Generate trading signals from various data sources."""

from __future__ import annotations

import os
import logging
import datetime
import math
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from indicators import haco as haco_indicator, haco_ha, hacolt, common as indicator_common

from .mode_profiles import MODE_PROFILES
from .quotes import fetch_latest_prices

try:
    import openai  # optional
except Exception:  # pragma: no cover - optional dep
    openai = None

POSITIVE_WORDS = {"gain", "growth", "bull", "optimistic", "up"}
NEGATIVE_WORDS = {"loss", "drop", "bear", "pessimistic", "down"}

# Exit strategy configuration
EXIT_PROFIT_TARGET_PCT = 0.05  # 5% profit target
EXIT_STOP_LOSS_PCT = 0.02     # 2% stop-loss
EXIT_MAX_HOLD_DAYS = 30       # time-based exit after 30 trading days

DEFAULT_WATCHLIST = ["SPY", "QQQ", "DIA", "IWM", "AAPL", "MSFT", "NVDA"]
DEFAULT_ADVANCED_TABS = [
    {
        "id": "playbook",
        "title": "Playbook",
        "content": [
            "Review macro tone and sector strength before the open.",
            "Stagger entries to avoid chasing extended moves.",
            "Lock gains aggressively when readiness deteriorates.",
        ],
    },
    {
        "id": "checklist",
        "title": "Checklist",
        "content": [
            "Is trend aligned across the chosen timeframe?",
            "Do momentum and volume confirm the move?",
            "Have risk parameters been staged?",
        ],
    },
]


def _get_mode_profile(mode: str) -> tuple[str, dict]:
    """Return the canonical mode key and its profile definition."""

    canonical = (mode or "swing").strip().lower()
    profile = MODE_PROFILES.get(canonical)
    if profile is None:
        canonical = "swing"
        profile = MODE_PROFILES[canonical]
    return canonical, profile


def _goal_lines_for_mode(mode_key: str) -> dict:
    m = (mode_key or "swing").lower()
    if m == "day":       return dict(rsi=52, adx=20, vol_mult=1.10)
    if m == "position":  return dict(rsi=55, adx=20, vol_mult=1.10)
    if m == "crypto":    return dict(rsi=55, adx=23, vol_mult=1.20)
    # swing default
    return dict(rsi=55, adx=25, vol_mult=1.15)


def _to_pct(value: float, lo: float, hi: float) -> float:
    if hi == lo: return 0.0
    v = max(lo, min(hi, float(value)))
    return float((v - lo) / (hi - lo) * 100.0)


def _to_float(x, default: float = 0.0) -> float:
    """Coerce pandas/ndarray/scalar to a plain float, mapping NaN/None to default."""
    try:
        if isinstance(x, pd.Series):
            x = x.iloc[0] if len(x) else default
        elif isinstance(x, np.ndarray):
            x = x.item() if x.size else default
        x = float(x)
        return x if not math.isnan(x) else default
    except Exception:
        return default


def _fallback_history() -> pd.DataFrame:
    """Return a deterministic synthetic price series for offline operation."""

    now = pd.Timestamp.utcnow()
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")
    idx = pd.date_range(end=now, periods=90, freq="D")
    base = 100.0
    closes = [base + math.sin(i / 5) * 2 + i * 0.2 for i in range(len(idx))]
    opens = [c * (1 - 0.002) for c in closes]
    highs = [max(o, c) * 1.01 for o, c in zip(opens, closes)]
    lows = [min(o, c) * 0.99 for o, c in zip(opens, closes)]
    volume = [1_000_000 + (i % 5) * 50_000 for i in range(len(idx))]
    data = {
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volume,
    }
    return pd.DataFrame(data, index=idx)


def _load_history(symbol: str, profile: dict) -> pd.DataFrame:
    period = profile.get("period", "6mo")
    interval = profile.get("interval", "1d")
    try:
        history = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        logging.exception("Failed to download price history for %s", symbol)
        history = pd.DataFrame()
    if history.empty:
        return _fallback_history()
    history = history.dropna(how="all")
    history.index = pd.to_datetime(history.index, utc=True)
    if "Close" not in history and "Adj Close" in history:
        history = history.rename(columns={"Adj Close": "Close"})
    return history.tail(max(120, profile.get("lookback_days", 120)))


def _prepare_candles(history: pd.DataFrame) -> list[dict]:
    candles: list[dict] = []
    for ts, row in history.iterrows():
        timestamp = pd.Timestamp(ts)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        try:
            epoch = int(timestamp.timestamp())
        except Exception:
            epoch = int(pd.Timestamp.utcnow().timestamp())
        candles.append({
            "time": epoch,
            "o": _scalar(row.get("Open", row.get("open", 0.0))),
            "h": _scalar(row.get("High", row.get("high", 0.0))),
            "l": _scalar(row.get("Low",  row.get("low",  0.0))),
            "c": _scalar(row.get("Close",row.get("close", 0.0))),
            "v": _scalar(row.get("Volume",row.get("volume", 0.0))),
        })
    return candles


def _component_scores(history: pd.DataFrame, profile: dict, candles: list[dict]) -> tuple[list[dict], float, dict]:
    chart_cfg = profile.get("chart", {})
    closes = history.get("Close", pd.Series(dtype=float)).astype(float)
    volumes = history.get("Volume")
    trend_window = chart_cfg.get("trend_window", 34)
    momentum_window = chart_cfg.get("momentum_window", 14)
    volume_window = chart_cfg.get("volume_window", 20)

    # Trend (HACOLT delta over a small lookback)
    core_candles = [{"o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"]} for c in candles]
    trend_series = hacolt.compute_trend(core_candles, period=trend_window) if candles else []
    if trend_series:
        lookback = min(len(trend_series) - 1, max(3, trend_window // 4))
        trend_delta = trend_series[-1] - trend_series[-lookback - 1]
    else:
        trend_delta = 0.0
    trend_score = indicator_common.normalise_score(trend_delta, lower=-5.0, upper=5.0)
    trend_status = "bullish" if trend_delta > 0 else "bearish" if trend_delta < 0 else "neutral"

    # Momentum
    if len(closes) > max(1, momentum_window):
        raw_ref = closes.iloc[-momentum_window] if len(closes) > momentum_window else closes.iloc[0]
    else:
        raw_ref = closes.iloc[0] if len(closes) else 0.0
    ref = _to_float(raw_ref, 0.0)
    last_close = _to_float(closes.iloc[-1] if len(closes) else 0.0, 0.0)
    momentum = ((last_close / ref) - 1.0) if ref != 0.0 else 0.0
    momentum_score = indicator_common.normalise_score(momentum, lower=-0.08, upper=0.08)
    momentum_status = "accelerating" if momentum > 0 else "fading" if momentum < 0 else "flat"

    # Realized vol proxy (lower vol → higher score)
    returns = closes.pct_change().dropna()
    if not returns.empty:
        vol_window = min(len(returns), max(5, momentum_window))
        vol_value = returns.rolling(vol_window).std().dropna()
        volatility = _scalar(vol_value.iloc[-1]) if not vol_value.empty else _scalar(returns.std())
    else:
        volatility = 0.0
    volatility_score = indicator_common.normalise_score(0.06 - volatility, lower=-0.06, upper=0.06)
    volatility_status = "calm" if volatility < 0.03 else "elevated" if volatility > 0.06 else "balanced"

    # Volume ratio & multiple
    if volumes is not None and not volumes.dropna().empty:
        avg_volume  = _scalar(volumes.rolling(volume_window).mean().iloc[-1])
        last_volume = _scalar(volumes.iloc[-1])
        volume_ratio = (last_volume - avg_volume) / avg_volume if avg_volume != 0.0 else 0.0
        vol_mult = (last_volume / avg_volume) if avg_volume != 0.0 else 0.0
    else:
        volume_ratio = 0.0
        vol_mult = 0.0
    volume_score = indicator_common.normalise_score(volume_ratio, lower=-1.0, upper=1.0)
    volume_status = "surging" if volume_ratio > 0.2 else "fading" if volume_ratio < -0.2 else "steady"

    components = [
        {"id": "trend",     "title": "Trend",      "score": round(trend_score, 1),     "status": trend_status,     "value": round(trend_delta, 3)},
        {"id": "momentum",  "title": "Momentum",   "score": round(momentum_score, 1),  "status": momentum_status,  "value": round(momentum, 3)},
        {"id": "volatility","title": "Volatility", "score": round(volatility_score, 1),"status": volatility_status,"value": round(volatility, 3)},
        {"id": "volume",    "title": "Volume",     "score": round(volume_score, 1),    "status": volume_status,    "value": round(volume_ratio, 3)},
    ]

    readiness_score = round(sum(c["score"] for c in components) / len(components), 1)
    meta = {"volume_mult": float(vol_mult)}
    return components, readiness_score, meta


def _chart_payload(candles: list[dict], trend_series: list[float]) -> dict:
    if not candles:
        return {"candles": [], "heikin_ashi": [], "indicators": {}}

    ha_input = [{"o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"]} for c in candles]
    ha = haco_ha.project(ha_input)
    ha_payload = [
        {
            "time": candles[idx]["time"],
            "o": round(item["o"], 4),
            "h": round(item["h"], 4),
            "l": round(item["l"], 4),
            "c": round(item["c"], 4),
        }
        for idx, item in enumerate(ha)
    ]

    closes = [c["c"] for c in candles]
    sma20 = indicator_common.sma(closes, 20)
    sma50 = indicator_common.sma(closes, 50)

    indicators = {
        "sma20": [
            {"time": candles[i]["time"], "value": round(val, 4)}
            for i, val in enumerate(sma20)
            if val is not None
        ],
        "sma50": [
            {"time": candles[i]["time"], "value": round(val, 4)}
            for i, val in enumerate(sma50)
            if val is not None
        ],
    }

    if trend_series:
        aligned = trend_series[-len(candles) :]
        indicators["trend"] = [
            {"time": candles[-len(aligned) + idx]["time"], "value": round(value, 4)}
            for idx, value in enumerate(aligned)
        ]

    return {
        "candles": candles,
        "heikin_ashi": ha_payload,
        "indicators": indicators,
    }


def compute_signals(symbol: str, mode: str = "swing") -> dict:
    canonical_mode, profile = _get_mode_profile(mode)
    mode_key = canonical_mode
    goals = _goal_lines_for_mode(mode_key)

    history = _load_history(symbol, profile)
    candles = _prepare_candles(history)

    # compute trend ONCE for chart & HACOLT meta
    trend_series = hacolt.compute_trend(
        ({"o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"]} for c in candles),
        period=profile.get("chart", {}).get("trend_window", 34),
    ) if candles else []

    components, readiness_score, comps_meta = _component_scores(history, profile, candles)
    vol_mult = float(comps_meta.get("volume_mult", 0.0))
    chart = _chart_payload(candles, trend_series)

    last_close = _scalar(history["Close"].iloc[-1]) if not history.empty else None
    action_bias = "long" if readiness_score >= 55 else "short" if readiness_score <= 40 else "neutral"
    entries = [{
        "type": action_bias,
        "confidence": readiness_score,
        "summary": f"Trend is {components[0]['status']} and momentum is {components[1]['status']}.",
        "price": format_price(last_close) if last_close is not None else None,
    }]

    # defaults so meta never NameErrors
    trend_pass = False
    _last_adx = 0.0

    exits_payload, exit_reason = (None, "")
    panels = []  # will fill if we can compute display stats

    if last_close is not None:
        exits_payload, exit_reason = _exit_levels(symbol, "buy" if action_bias != "short" else "sell", float(last_close))

        closes = history.get("Close", pd.Series(dtype=float)).astype(float)

        def _rsi(series: pd.Series, length: int = 14) -> float:
            # Ensure 1-D float array
            arr = np.asarray(series, dtype=float)
            if arr.ndim > 1:
                arr = np.squeeze(arr)           # drop singleton dims, e.g. (N,1) -> (N,)
            arr = arr.ravel()                   # guarantee 1-D
        
            if arr.size < 2:
                return 0.0
        
            s = pd.Series(arr)
            delta = s.diff()
            up = delta.clip(lower=0.0)
            down = -delta.clip(upper=0.0)
        
            roll_up = up.ewm(span=length, adjust=False).mean()
            roll_down = down.ewm(span=length, adjust=False).mean()
        
            rs = roll_up / roll_down.replace(0.0, np.nan)
            rsi_series = 100 - (100 / (1 + rs))
        
            val = rsi_series.iloc[-1]
            return float(val) if not pd.isna(val) else 0.0

        last_rsi = _rsi(closes, 14)
        prev_rsi = _rsi(closes.iloc[:-1], 14) if len(closes) > 15 else last_rsi
        rising = last_rsi >= prev_rsi

        from indicators.common import adx as _adx
        _last_adx = float(_adx(history["High"], history["Low"], history["Close"], 14).iloc[-1]) if not history.empty else 0.0

        price  = _scalar(history["Close"].iloc[-1]) if not history.empty else 0.0
        ema50  = _scalar(history["Close"].ewm(span=50,  adjust=False).mean().iloc[-1]) if len(history) else 0.0
        ema200 = _scalar(history["Close"].ewm(span=200, adjust=False).mean().iloc[-1]) if len(history) else 0.0
        trend_pass = (price > ema50 > ema200) or (ema50 > ema200)

        panels = [
            {
                "id": "trend",
                "title": "Trend",
                "status": "PASS" if trend_pass else "FAIL",
                "score": next(c["score"] for c in components if c["id"] == "trend"),
                "goal": "Close > EMA50 > EMA200",
                "goal_pct": 70,
                "reason": f"Close {price:.2f} vs EMA50 {ema50:.2f} / EMA200 {ema200:.2f}",
                "summary": f"Trend is {'aligned' if trend_pass else 'mixed'}.",
            },
            {
                "id": "momentum",
                "title": "Momentum",
                "status": "PASS" if (last_rsi >= goals["rsi"] and rising) else "FAIL",
                "score": next(c["score"] for c in components if c["id"] == "momentum"),
                "goal": f"RSI ≥ {goals['rsi']} & rising",
                "goal_pct": _to_pct(goals["rsi"], 40, 70),
                "reason": f"RSI14={last_rsi:.1f} ({'↑' if rising else '↓'})",
                "summary": f"RSI {last_rsi:.1f} {'rising' if rising else 'falling'}; goal ≥ {goals['rsi']}.",
            },
            {
                "id": "volatility",
                "title": "Volatility/Trend Strength (ADX)",
                "status": "PASS" if _last_adx >= goals["adx"] else "FAIL",
                "score": next(c["score"] for c in components if c["id"] == "volatility"),
                "goal": f"ADX ≥ {goals['adx']}",
                "goal_pct": _to_pct(goals["adx"], 10, 40),
                "reason": f"ADX14={_last_adx:.1f}",
                "summary": f"ADX { _last_adx:.1f } vs {goals['adx']}.",
            },
            {
                "id": "volume",
                "title": "Volume",
                "status": "PASS" if (vol_mult >= goals["vol_mult"]) else "FAIL",
                "score": next(c["score"] for c in components if c["id"] == "volume"),
                "goal": f"Vol ≥ {goals['vol_mult']:.2f}× avg",
                "goal_pct": _to_pct(goals["vol_mult"], 0.8, 1.3),
                "reason": f"Vol={vol_mult:.2f}× avg",
                "summary": f"Volume {vol_mult:.2f}× avg; goal {goals['vol_mult']:.2f}×.",
            },
        ]

    # HACOLT mini-bars (0/50/100)
    hacolt_state_series = []
    if trend_series:
        for i in range(len(trend_series)):
            if i == 0:
                hacolt_state_series.append(50)
            else:
                up = trend_series[i] >= trend_series[i - 1]
                hacolt_state_series.append(100 if up else 0)
    chart["hacolt"] = (
        [{"time": c["time"], "value": int(hacolt_state_series[idx])}
         for idx, c in enumerate(chart["candles"][-len(hacolt_state_series):])]
        if chart["candles"] else []
    )

    payload_meta = {
        "trend_pass": bool(trend_pass),
        "adx": float(_last_adx),
        "hacolt_now": int(hacolt_state_series[-1] if hacolt_state_series else 50),
    }

    # Advanced tabs (merge profile + defaults, no duplicates by id)
    advanced_tabs = [
        {"id": "mindset", "title": "Mindset", "content": profile.get("mindset", {}).get("focus", [])},
        {"id": "playbook", "title": "Playbook", "content": profile.get("playbook", [])},
    ]
    used = {t["id"] for t in advanced_tabs}
    for tab in DEFAULT_ADVANCED_TABS:
        if tab["id"] not in used:
            advanced_tabs.append(tab)

    readiness = {"score": readiness_score, "components": components}

    return {
        "symbol": symbol.upper(),
        "mode": canonical_mode,
        "panels": panels,
        "readiness": readiness,
        "entries": entries,
        "exits": {"levels": exits_payload, "reason": exit_reason},
        "chart": chart,
        "chart_preset": {
            "interval": profile.get("interval", "1d"),
            "period": profile.get("period", "6mo"),
        },
        "advanced_tabs": advanced_tabs,
        "available_modes": sorted(MODE_PROFILES.keys()),
        "watchlist": profile.get("watchlist", DEFAULT_WATCHLIST),
        "mindset": profile.get("mindset", {}),
        "meta": payload_meta,
    }


def get_watchlist(mode: str | None = None) -> list[str]:
    """Return the configured watchlist for ``mode`` or the default list."""

    canonical_mode, profile = _get_mode_profile(mode or "swing")
    watchlist = profile.get("watchlist")
    if isinstance(watchlist, list) and watchlist:
        return [str(sym).upper() for sym in watchlist]
    return DEFAULT_WATCHLIST


def format_price(value: float | None) -> float | None:
    """Return value rounded to 5 decimals when under $1, otherwise 2 decimals."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(value, 5) if abs(value) < 1 else round(value, 2)


def get_risk_factors(symbols: list[str]) -> dict:
    """Return a mapping of symbol to Quiver risk score."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/riskfactors",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                scores = {}
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym:
                        score = item.get("RiskScore") or item.get("Score")
                        try:
                            scores[sym] = float(score)
                        except (TypeError, ValueError):
                            pass
                return scores
    except Exception:
        pass
    return {}


def get_whale_moves(limit: int = 5) -> list[dict]:
    """Return recent whale moves from Quiver."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/whalemoves",
            headers=headers,
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return data[:limit]
    except Exception:
        pass
    return []


async def fetch_unusual_whales(limit: int = 5) -> list[dict]:
    """Fetch latest unusual whale alerts."""
    import httpx

    key = os.getenv("WHALES_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.unusualwhales.com/alerts", headers=headers
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    data = data.get("results", data)
                if isinstance(data, list):
                    return data[:limit]
    except Exception:
        pass
    return []


def get_political_moves(symbols: list[str]) -> dict:
    """Return counts of recent congressional trades for each symbol."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/congresstrading",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            counts: dict[str, int] = {}
            if isinstance(data, list):
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym and sym in symbols:
                        counts[sym] = counts.get(sym, 0) + 1
            return counts
    except Exception:
        pass
    return {}


def get_lobby_disclosures(symbols: list[str]) -> dict:
    """Return counts of recent lobbying disclosures for each symbol."""
    key = os.getenv("QUIVER_API_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        r = requests.get(
            "https://api.quiverquant.com/beta/live/lobbying",
            headers=headers,
            params={"tickers": ",".join(symbols)},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            counts: dict[str, int] = {}
            if isinstance(data, list):
                for item in data:
                    sym = item.get("Ticker") or item.get("ticker")
                    if sym and sym in symbols:
                        counts[sym] = counts.get(sym, 0) + 1
            return counts
    except Exception:
        pass
    return {}


def news_sentiment_signal(symbol: str) -> dict:
    """Return a sentiment score based on recent financial news headlines."""
    params = {"q": symbol, "pageSize": 5}
    key = os.getenv("NEWSAPI_KEY")
    if key:
        params["apiKey"] = key
    articles: list[str] = []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params=params,
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            articles = [a.get("title", "") for a in data.get("articles", [])[:5]]
    except Exception:
        articles = []
    analyzer = SentimentIntensityAnalyzer()
    score = 0.0
    for title in articles:
        score += analyzer.polarity_scores(title)["compound"]
    return {
        "type": "news_sentiment",
        "symbol": symbol,
        "score": round(score, 2),
    }


def technical_indicator_signal(symbol: str) -> dict:
    """Generate a simple moving-average crossover signal."""
    data = yf.download(
        symbol,
        period="3mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=True,
    )
    # Guard: yfinance may return None/empty
    if data is None or data.empty:
        return {"type": "technical", "symbol": symbol, "signal": "none"}

    data["ma_short"] = data["Close"].rolling(20).mean()
    data["ma_long"]  = data["Close"].rolling(50).mean()
    signal = "bullish" if data["ma_short"].iloc[-1] > data["ma_long"].iloc[-1] else "bearish"
    return {"type": "technical", "symbol": symbol, "signal": signal}


def macro_llm_signal(text: str) -> dict:
    """Use an LLM to interpret macroeconomic commentary."""
    if openai and os.getenv("OPENAI_API_KEY"):
        try:  # pragma: no cover - external call
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Given the following macroeconomic summary, "
                            "respond with one word: bullish, bearish, or neutral.\n" + text
                        ),
                    }
                ],
            )
            outlook = resp.choices[0].message["content"].strip()
            return {"type": "macro_llm", "outlook": outlook}
        except Exception:
            pass
    return {"type": "macro_llm", "outlook": "unknown"}

def _scalar(x, default=0.0):
    # Pull a single numeric out of Series/ndarray/Scalar
    if isinstance(x, pd.Series):
        x = x.iloc[0] if len(x) else default
    elif isinstance(x, np.ndarray):
        x = x.item() if x.size else default
    return float(x) if pd.notna(x) else float(default)


def _calculate_exit(symbol, data, entry_price, take_profit_pct=0.02, stop_loss_pct=0.01, **kwargs):
    """Return exit recommendation based on latest price targets."""
    close_series = None
    if isinstance(data, pd.DataFrame):
        if "Close" in data:
            close_series = data["Close"]
        elif "Adj Close" in data:
            close_series = data["Adj Close"]
    if close_series is None or len(close_series) == 0:
        return {"rec": "hold", "reason": "no price"}

    last_close = float(close_series.iloc[-1])
    if math.isnan(last_close):
        return {"rec": "hold", "reason": "no price"}

    profit_target = float(entry_price) * (1.0 + float(take_profit_pct))
    stop_target   = float(entry_price) * (1.0 - float(stop_loss_pct))

    if last_close >= profit_target:
        return {"rec": "sell", "reason": f"Target {profit_target:.2f}"}
    if last_close <= stop_target:
        return {"rec": "sell", "reason": f"Stop {stop_target:.2f}"}
    return {"rec": "hold", "reason": "Within band"}


def _calculate_exit_date(
    symbol: str, entry_price: float, entry_date: datetime.date
) -> tuple[datetime.date, float]:
    """Return exit date and price based on fixed target, stop and time limit."""
    forward = None
    exit_date = None
    exit_price = None
    try:
        forward = yf.download(
            symbol,
            start=entry_date,
            period=f"{EXIT_MAX_HOLD_DAYS}d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        profit_target = _scalar(entry_price) * (1 + EXIT_PROFIT_TARGET_PCT)
        stop_loss = _scalar(entry_price) * (1 - EXIT_STOP_LOSS_PCT)
        for date, row in forward.iterrows():
            price = _scalar(row["Close"])
            if price is None:
                continue
            if price >= profit_target:
                exit_date, exit_price = date.date(), profit_target
                break
            if price <= stop_loss:
                exit_date, exit_price = date.date(), stop_loss
                break
        if exit_date is None and forward is not None and not forward.empty:
            last_date = forward.index[-1].date()
            exit_date = last_date
            exit_price = _scalar(forward.iloc[-1]["Close"])
    except Exception:
        logging.exception("Exit calculation failed for %s", symbol)
    if exit_date is None:
        exit_date = entry_date + datetime.timedelta(days=EXIT_MAX_HOLD_DAYS)
        exit_price = _scalar(entry_price)
    return exit_date, float(exit_price)


def _exit_levels(symbol: str, action: str, price: float) -> tuple[dict | None, str]:
    """Return low/medium/high risk exit levels and an explanation."""
    try:
        data = yf.download(
            symbol, period="2mo", interval="1d",
            auto_adjust=False, progress=False, threads=True,
        )
        if data is None or data.empty:
            return None, "No historical data for exits"

        high = data["High"].astype(float)
        low  = data["Low"].astype(float)
        close = data["Close"].astype(float)

        # Need enough bars; otherwise, bail early with a friendly reason.
        n = len(close)
        if n < 20:
            return None, "Not enough history for exits"

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)

        atr_val = _scalar(tr.rolling(14, min_periods=14).mean().iloc[-1])
        sup_val = _scalar(low.rolling(20,  min_periods=20).min().iloc[-1])
        res_val = _scalar(high.rolling(20, min_periods=20).max().iloc[-1])

        # Guard NaNs
        if any(math.isnan(v) for v in (atr_val, sup_val, res_val)):
            return None, "Insufficient data quality for exits"

        if action == "buy":
            exits = {
                "low":    format_price(price + atr_val),
                "medium": format_price(price + 2 * atr_val),
                "high":   format_price(max(res_val, price + 3 * atr_val)),
            }
        else:
            exits = {
                "low":    format_price(price - atr_val),
                "medium": format_price(price - 2 * atr_val),
                "high":   format_price(min(sup_val, price - 3 * atr_val)),
            }

        reason = f"ATR {atr_val:.2f}, support {sup_val:.2f}, resistance {res_val:.2f}."
        return exits, reason
    except Exception:
        return None, "Exit calculation failed"


def generate_recommendations(symbols: list[str]) -> list[dict]:
    """Return simple trade recommendations based on sentiment, technicals, and risk."""
    recs = []
    risk_scores = get_risk_factors(symbols)
    political = get_political_moves(symbols)
    lobby = get_lobby_disclosures(symbols)
    prices = fetch_latest_prices(symbols)
    for sym in symbols:
        news = news_sentiment_signal(sym)
        tech = technical_indicator_signal(sym)
        price = prices.get(sym)
        base_score = news.get("score", 0) + (1 if tech.get("signal") == "bullish" else -1)
        risk = risk_scores.get(sym, 0)
        pol = political.get(sym, 0)
        lob = lobby.get(sym, 0)
        score = base_score - risk + 0.2 * pol + 0.1 * lob
        action = "buy" if score >= 0 else "sell"
        entry_date = datetime.date.today()
        entry_price = price
        exit_date = None
        exit_price = None
        if entry_price is not None:
            exit_date, exit_price = _calculate_exit_date(sym, entry_price, entry_date)
        probability = round(min(0.9, 0.5 + min(abs(score) / 10, 0.4)), 2)
        parts = [
            f"News score {news.get('score')} and {tech.get('signal')} MA signal",
            f"risk {risk}"
        ]
        if pol:
            parts.append(f"{pol} political moves")
        if lob:
            parts.append(f"{lob} lobby disclosures")
        reason = " ".join(parts) + f" suggest {action}."
        recs.append({
            "symbol": sym,
            "action": action,
            "entry_date": entry_date.isoformat(),
            "entry_price": format_price(entry_price),
            "exit_date": exit_date.isoformat() if exit_date else None,
            "exit_price": format_price(exit_price),
            "probability": probability,
            "reason": reason,
        })
    recs.sort(key=lambda x: x["probability"], reverse=True)
    return recs[:3]
