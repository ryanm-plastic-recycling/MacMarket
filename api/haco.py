from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional
import time

router = APIRouter(prefix="/api/signals/haco", tags=["haco"])


class ScanReq(BaseModel):
    symbol: str


def _resolve_symbol(
    symbol: Optional[str] = Query(None, alias="symbol"),
    ticker: Optional[str] = Query(None, alias="ticker"),
    body: Optional[ScanReq] = Body(None),
):
    """Accept symbol from body or either query param name."""
    s = (body.symbol if body else None) or symbol or ticker
    if not s or not s.strip():
        # 400 (not 422) so frontend handles cleanly
        raise HTTPException(status_code=400, detail="symbol_required")
    return s.strip().upper()


def _stub_payload(sym: str):
    now = int(time.time())
    candles = []
    # 50 hourly bars, gently moving so chart is visibly alive
    base = 100.0
    for i in range(50):
        t = now - (50 - i) * 3600
        o = base + i * 0.2
        c = o + (0.5 if i % 2 else -0.3)
        h = max(o, c) + 0.6
        l = min(o, c) - 0.6
        candles.append({"time": t, "open": o, "high": h, "low": l, "close": c})
    markers = [
        {
            "time": candles[-1]["time"],
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "green",
            "text": f"HACO {sym}",
        }
    ]
    return {"candles": candles, "markers": markers}


@router.post("/scan")
async def scan_post(payload: ScanReq = Body(...)):
    sym = _resolve_symbol(body=payload)
    return _stub_payload(sym)


@router.get("/scan")
async def scan_get(
    symbol: Optional[str] = Query(None, alias="symbol"),
    ticker: Optional[str] = Query(None, alias="ticker"),
):
    sym = _resolve_symbol(symbol=symbol, ticker=ticker)
    return _stub_payload(sym)

