"""Signals API router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..mode_profiles import MODE_PROFILES, WATCHLIST_SYMBOLS
from ..services.signals_engine import compute_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/{symbol}")
def get_signals(symbol: str, mode: str = Query("swing", description="Trading mode")):
    try:
        payload = compute_signals(symbol, mode)
    except ValueError as exc:  # pragma: no cover - network errors are runtime issues
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload["available_modes"] = [
        {"id": key, "name": profile.name, "timeframes": profile.tf}
        for key, profile in MODE_PROFILES.items()
    ]
    payload["watchlist"] = WATCHLIST_SYMBOLS
    payload["mindset"] = {
        "day": "1–15m focus. Tight stops (<1%). VWAP anchors intraday bias.",
        "swing": "1h–1D cadence. Hold 1–10 days. ATR-based swing management.",
        "position": "1D–1W trend participation. Hold weeks to months.",
        "crypto": "4h–1D rhythm. 24/7 tape—watch weekend liquidity gaps.",
    }
    return payload
