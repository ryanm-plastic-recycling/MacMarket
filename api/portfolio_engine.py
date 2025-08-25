"""Simple portfolio engine for QuiverQuant strategies."""
from __future__ import annotations
from decimal import Decimal
from typing import Dict
from datetime import date, timedelta

from . import qq_dal, price_service


def _rescale_allocations(allocs, tolerance: float) -> bool:
    total = sum(float(a["target_weight"]) for a in allocs)
    if abs(total - 1.0) > tolerance:
        return False
    if total != 1.0 and total > 0:
        for a in allocs:
            a["target_weight"] = Decimal(a["target_weight"]) / Decimal(total)
    return True


def run_rebalances_for_unprocessed() -> Dict[str, int]:
    """Very small portfolio engine that validates allocations and marks rebalances processed."""
    processed = 0
    for reb in qq_dal.fetch_pending_rebalances():
        strategy = qq_dal.get_strategy(reb["strategy_id"])
        allocs = qq_dal.fetch_allocations(reb["id"])
        tol = float(strategy.get("target_sum_tolerance_pct", 0.01))
        if not _rescale_allocations(allocs, tol):
            qq_dal.mark_rebalance_status(reb["id"], "skipped", "weights do not sum to 1")
            continue
        # ensure prices for fill date
        tickers = [a["ticker"] for a in allocs]
        fill = price_service.next_trading_day(reb["rebalance_date"])
        price_service.ensure_prices(tickers, fill, fill)
        qq_dal.mark_rebalance_status(reb["id"], "processed")
        processed += 1
    return {"processed": processed}


def materialize_nav_positions(backfill: bool = False) -> None:
    """Placeholder for NAV/position materialization."""
    return None
