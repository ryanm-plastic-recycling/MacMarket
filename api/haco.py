from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import time
import math
import pandas as pd
import yfinance as yf


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
    """Length of current consecutive True (1) run at each index."""
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
    lookback: int,
    show_ha: bool,
):
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
    ha = _heikin_ashi(df)
    up_run = _consecutive(ha["upbar"])
    dn_run = _consecutive(1 - ha["upbar"])

    # Up/Down warnings: raised when a consecutive-run hits threshold on this bar
    upw = (up_run >= max(1, len_up)) & (
        up_run.shift(1, fill_value=0) < max(1, len_up)
    )
    dnw = (dn_run >= max(1, len_dn)) & (
        dn_run.shift(1, fill_value=0) < max(1, len_dn)
    )

    # Optional "ZL" lines (very lightweight proxies)
    zl_ha_u = ha["close"].where(ha["upbar"] == 1)
    zl_cl_u = df["Close"].where(ha["upbar"] == 1)
    zl_ha_d = ha["close"].where(ha["upbar"] == 0)
    zl_cl_d = df["Close"].where(ha["upbar"] == 0)

    out: List[dict] = []
    for ts, row in df.iterrows():
        sec = int(ts.to_pydatetime().timestamp())
        i = df.index.get_loc(ts)
        # choose price source based on HA toggle (UI asks "Show Heikin-Ashi")
        if show_ha:
            o, h, l, c = (
                float(ha["open"].iloc[i]),
                float(ha["high"].iloc[i]),
                float(ha["low"].iloc[i]),
                float(ha["close"].iloc[i]),
            )
        else:
            o, h, l, c = (
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
            )
        out.append(
            {
                "time": sec,
                "o": o,
                "h": h,
                "l": l,
                "c": c,
                "state": bool(ha["upbar"].iloc[i]),
                "upw": bool(upw.iloc[i]),
                "dnw": bool(dnw.iloc[i]),
                "ZlHaU": float(zl_ha_u.iloc[i])
                if not math.isnan(zl_ha_u.iloc[i])
                else None,
                "ZlClU": float(zl_cl_u.iloc[i])
                if not math.isnan(zl_cl_u.iloc[i])
                else None,
                "ZlHaD": float(zl_ha_d.iloc[i])
                if not math.isnan(zl_ha_d.iloc[i])
                else None,
                "ZlClD": float(zl_cl_d.iloc[i])
                if not math.isnan(zl_cl_d.iloc[i])
                else None,
            }
        )

    last = out[-1]
    # crude "reasons" string; good enough for UI
    reasons: List[str] = []
    reasons.append("HA up" if last["state"] else "HA down")
    if last["upw"]:
        reasons.append(f"run≥{len_up}")
    if last["dnw"]:
        reasons.append(f"run≥{len_dn}")
    return {
        "series": out,
        "last": {
            "state": last["state"],
            "upw": last["upw"],
            "dnw": last["dnw"],
            "reasons": ", ".join(reasons),
        },
    }


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
    return _build_series(
        symbol.strip().upper(),
        timeframe,
        lengthUp,
        lengthDown,
        lookback,
        bool(showHa),
    )


@router.get("/scan")
def haco_scan(
    symbols: str = Query(..., description="Comma separated symbols"),
    timeframe: str = Query("Day"),
):
    """Return last-bar HACO flags for many symbols (for the HACO table)."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        return []
    out = []
    for s in syms:
        try:
            data = _build_series(s, timeframe, 34, 34, 200, False)
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

