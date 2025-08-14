from fastapi import APIRouter, HTTPException

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


