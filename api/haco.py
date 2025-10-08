from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import time
import math
import pandas as pd, numpy as np
import yfinance as yf
import inspect
from indicators.haco import compute_haco


router = APIRouter(prefix="/api/signals/haco", tags=["haco"])


def _parse_timeframe(tf: str) -> tuple[str, str]:
    """Return (interval, period) for yfinance."""
    s = (tf or "day").strip().lower()
    if s in {"h", "1h", "hour"}:
        return "1h", "730d"  # yfinance limit for 1h
    if s in {"w", "1w", "1wk", "week"}:
        return "1wk", "10y"
    if s in {"m", "1m", "1mo", "month"}:
        return "1mo", "max"
    # default day
    return "1d", "3y"


def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Compute basic Heikin-Ashi columns and a simple state."""
    ha = pd.DataFrame(index=df.index)
    ha["close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha["open"] = (df["Open"] + df["Close"]) / 2.0
    # iterative HA open
    for i in range(1, len(ha)):
        ha.iloc[i, ha.columns.get_loc("open")] = (
            ha["open"].iloc[i - 1] + ha["close"].iloc[i - 1]
        ) / 2.0
    ha["high"] = pd.concat([df["High"], ha["open"], ha["close"]], axis=1).max(axis=1)
    ha["low"] = pd.concat([df["Low"], ha["open"], ha["close"]], axis=1).min(axis=1)
    ha["upbar"] = (ha["close"] > ha["open"]).astype(int)
    return ha


def _consecutive(arr: pd.Series) -> pd.Series:
    """(Unused now) Length of current consecutive True (1) run at each index."""
    out = []
    run = 0
    for v in arr.astype(bool).tolist():
        run = run + 1 if v else 0
        out.append(run)
    return pd.Series(out, index=arr.index)


def _build_series(
    symbol: str,
    timeframe: str,
    len_up: int,
    len_dn: int,
    alert_lb: int,
    lookback: int,
    show_ha: bool,
):
    """
    New: delegate HACO math to indicators.haco.compute_haco (MetaStock-faithful).
    Preserve response shape {"series":[...], "last": {...}}.
    Honor show_ha by overriding OHLC for charting only.
    """
    interval, period = _parse_timeframe(timeframe)
    try:
        df = yf.download(
            symbol, period=period, interval=interval, auto_adjust=False, progress=False
        )
    except Exception as e:  # pragma: no cover - network
        raise HTTPException(status_code=502, detail=f"download_failed: {e}")
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="no_data")

    df = df.dropna().tail(max(lookback, 200))
    # Build raw candles for compute_haco
    candles: List[Dict[str, Any]] = []
    for ts, row in df.iterrows():
        candles.append({
            "time": int(ts.to_pydatetime().timestamp()),
            "o": _scalar(row.get("Open", row.get("open", 0.0))),
            "h": _scalar(row.get("High", row.get("high", 0.0))),
            "l": _scalar(row.get("Low",  row.get("low",  0.0))),
            "c": _scalar(row.get("Close",row.get("close", 0.0))),
        })
    # MetaStock logic (already implemented in indicators.haco)
    out = compute_haco(
        candles=candles, length_up=len_up, length_down=len_dn, alert_lookback=alert_lb
    )
    series: List[Dict[str, Any]] = out["series"]
    last: Dict[str, Any] = out["last"]
    # Keep UI semantics: state as bool
    if series:
        for i in range(len(series)):
            series[i]["state"] = bool(series[i].get("state", 0))
    last["state"] = bool(last.get("state", 0))

    # Optional: override OHLC with Heikin-Ashi bars for chart display (no math changes)
    if show_ha and len(series) > 0:
        ha = _heikin_ashi(df)
        # Align on the same tail length used for series
        ha = ha.tail(len(series))
        ha_o = ha["open"].tolist()
        ha_h = ha["high"].tolist()
        ha_l = ha["low"].tolist()
        ha_c = ha["close"].tolist()
        for i in range(len(series)):
            series[i]["o"] = float(ha_o[i])
            series[i]["h"] = float(ha_h[i])
            series[i]["l"] = float(ha_l[i])
            series[i]["c"] = float(ha_c[i])

    return {"series": series, "last": last}


def _series_to_candles(series: List[Dict[str, Any]]):
    """Convert {time,o,h,l,c,...} to LW candlesticks + simple markers."""
    candles = [
        {
            "time": b["time"],
            "open": b["o"],
            "high": b["h"],
            "low": b["l"],
            "close": b["c"],
        }
        for b in series
    ]
    markers: List[Dict[str, Any]] = []
    for b in series:
        if b.get("upw"):
            markers.append(
                {
                    "time": b["time"],
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "color": "green",
                    "text": "HACO",
                }
            )
        if b.get("dnw"):
            markers.append(
                {
                    "time": b["time"],
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "color": "red",
                    "text": "HACO",
                }
            )
    return candles, markers


@router.get("")
def haco(
    symbol: str = Query(..., alias="symbol"),
    timeframe: str = Query("Day"),
    lengthUp: int = Query(34, ge=1),
    lengthDown: int = Query(34, ge=1),
    alertLookback: int = Query(1, ge=1),
    lookback: int = Query(200, ge=50),
    showHa: Optional[bool] = Query(False, alias="showHa"),
):
    """Return HACO bars for a single symbol."""
    params = {
        "symbol": symbol.strip().upper(),
        "timeframe": timeframe,
        "len_up": lengthUp,
        "len_dn": lengthDown,
        "lookback": lookback,
        "show_ha": bool(showHa),
    }
    if "alert_lb" in inspect.signature(_build_series).parameters:
        params["alert_lb"] = alertLookback
    return _build_series(**params)


@router.get("/scan")
def haco_scan(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols for table output"),
    symbol: Optional[str] = Query(None, description="Single symbol for chart output"),
    timeframe: str = Query("Day"),
):
    """Return HACO scan results: table or chart-friendly output."""
    # If single 'symbol' provided and no 'symbols', return chart data
    if symbol and not symbols:
        params = {
            "symbol": symbol.strip().upper(),
            "timeframe": timeframe,
            "len_up": 34,
            "len_dn": 34,
            "lookback": 200,
            "show_ha": False,
        }
        if "alert_lb" in inspect.signature(_build_series).parameters:
            params["alert_lb"] = 1
        data = _build_series(**params)
        candles, markers = _series_to_candles(data["series"])
        return {"candles": candles, "markers": markers}

    syms = [s.strip().upper() for s in (symbols or "").split(",") if s.strip()]
    if not syms:
        return []
    out = []
    for s in syms:
        try:
            params = {
                "symbol": s,
                "timeframe": timeframe,
                "len_up": 34,
                "len_dn": 34,
                "lookback": 200,
                "show_ha": False,
            }
            if "alert_lb" in inspect.signature(_build_series).parameters:
                params["alert_lb"] = 1
            data = _build_series(**params)
            ser = data["series"]
            if not ser:
                out.append({"symbol": s, "error": "no_data"})
                continue
            last = ser[-1]
            prev = ser[-2] if len(ser) > 1 else None
            changed = (prev is not None) and (
                bool(prev.get("state")) != bool(last.get("state"))
            )
            out.append(
                {
                    "symbol": s,
                    "upw": last.get("upw", False),
                    "dnw": last.get("dnw", False),
                    "state": last.get("state", None),
                    "changed": changed,
                    "reason": data["last"].get("reasons", ""),
                }
            )
        except HTTPException as ex:  # pragma: no cover - network errors
            out.append({"symbol": s, "error": ex.detail})
        except Exception as e:  # pragma: no cover - defensive
            out.append({"symbol": s, "error": str(e)})
    return out


@router.post("/scan")
def haco_scan_post(payload: Dict[str, Any] = Body(...)):
    """Chart compatibility: POST {"symbol": "..."} -> {candles, markers}."""
    sym = str(payload.get("symbol", "")).strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol_required")
    params = {
        "symbol": sym,
        "timeframe": "Day",
        "len_up": 34,
        "len_dn": 34,
        "lookback": 200,
        "show_ha": False,
    }
    if "alert_lb" in inspect.signature(_build_series).parameters:
        params["alert_lb"] = 1
    data = _build_series(**params)
    candles, markers = _series_to_candles(data["series"])
    return {"candles": candles, "markers": markers}

