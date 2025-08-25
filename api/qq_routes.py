"""FastAPI routes for QuiverQuant ingestion and portfolio engine."""
from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException

from . import qq_gmail, qq_parser, qq_dal, portfolio_engine

router = APIRouter(prefix="/api/qq", tags=["qq"])

DEFAULT_LABEL = os.getenv("GMAIL_LABEL", "Quiver Quantitative")
DEFAULT_QUERY = os.getenv(
    "GMAIL_QUERY",
    'label:"Quiver Quantitative" from:alerts@quiverquant.com subject:"Strategies in Your Watchlist are Trading Today" newer_than:30d',
)


@router.post("/ingest/latest")
def ingest_latest():
    service = qq_gmail.get_service()
    ids = qq_gmail.search_messages(service, DEFAULT_QUERY, DEFAULT_LABEL)
    ingested = 0
    strategies = []
    for mid in ids:
        if qq_dal.email_exists(mid):
            continue
        msg = qq_gmail.fetch_message_html(service, mid)
        email_id = qq_dal.upsert_email_ingest(msg)
        parsed = qq_parser.parse_email_html(msg["html"])
        for name, rdate, rows in parsed:
            sid = qq_dal.find_or_create_strategy(name)
            rid = qq_dal.upsert_rebalance(sid, rdate, email_id)
            for row in rows:
                qq_dal.upsert_allocation(rid, row)
            strategies.append(name)
        ingested += 1
    return {"emails": ingested, "strategies": list(set(strategies))}


@router.post("/run-rebalances")
def run_rebalances():
    return portfolio_engine.run_rebalances_for_unprocessed()


@router.get("/strategies")
def get_strategies():
    return {"data": qq_dal.get_strategies()}


@router.post("/strategies")
def upsert_strategy(payload: dict):
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="name required")
    sid = qq_dal.upsert_strategy(payload)
    return {"id": sid}


@router.get("/nav")
def get_nav(strategy_id: int, range: str | None = None):  # noqa: A002
    return {"data": qq_dal.get_nav(strategy_id, None, None)}


@router.get("/positions")
def get_positions(strategy_id: int, on: str):
    return {"data": qq_dal.get_positions(strategy_id, on)}


@router.get("/trades")
def get_trades(strategy_id: int, from_: str, to: str):
    return {"data": qq_dal.get_trades(strategy_id, from_, to)}


@router.get("/metrics")
def get_metrics(strategy_id: int, range: str | None = None):  # noqa: A002
    # Placeholder metrics - real implementation would compute stats
    nav = qq_dal.get_nav(strategy_id, None, None)
    return {"data": {"points": len(nav)}}
