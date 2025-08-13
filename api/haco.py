from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from indicators.haco import compute_haco
from services.data import get_candles

router = APIRouter(prefix="/api/signals", tags=["signals"])
page_router = APIRouter()

templates = Jinja2Templates(directory="templates")


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


@page_router.get("/signals/haco", response_class=HTMLResponse)
async def haco_page(request: Request):
    return templates.TemplateResponse("signals_haco.html", {"request": request})
