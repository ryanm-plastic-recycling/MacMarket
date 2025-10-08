"""Watchlist endpoint for Signals UI."""
from __future__ import annotations

from fastapi import APIRouter

from ..mode_profiles import WATCHLIST_SYMBOLS

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("/")
def get_watchlist():
    return {"symbols": WATCHLIST_SYMBOLS}
