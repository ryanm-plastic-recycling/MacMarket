from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from indicators.haco import compute_haco
from services.data import get_candles

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/haco")
def haco_api(
    symbol: str,
    timeframe: str = "Day",
    lengthUp: int = 34,
    lengthDown: int = 34,
    alertLookback: int = 1,
    lookback: int = 500,
):
    candles = get_candles(symbol, timeframe, lookback)
    if not candles:
        raise HTTPException(status_code=404, detail="No data")
    data = compute_haco(
        candles,
        length_up=lengthUp,
        length_down=lengthDown,
        alert_lookback=alertLookback,
    )
    return data


@router.get("/haco/scan")
def haco_scan(symbols: str, timeframe: str = "Day", lookback: int = 500):
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    out = []
    for sym in syms:
        try:
            candles = get_candles(sym, timeframe, lookback)
            data = compute_haco(candles)
            b = data["series"][-1] if data["series"] else {}
            out.append({
                "symbol": sym,
                "upw": bool(b.get("upw")),
                "dnw": bool(b.get("dnw")),
                "state": b.get("state"),
                "changed": bool(data["last"].get("changed")),
                "reason": b.get("reason", ""),
            })
        except Exception as e:
            out.append({"symbol": sym, "error": str(e)})
    return JSONResponse(out)


