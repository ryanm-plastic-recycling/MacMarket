"""Data access layer for QuiverQuant paper trading."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from backend.app.database import SessionLocal


def upsert_email_ingest(data: Dict[str, Any]) -> int:
    sql = text(
        """
        INSERT INTO qq_email_ingests (gmail_id, thread_id, subject, sender, received_at, snippet, html)
        VALUES (:message_id, :thread_id, :subject, :from, :received_at, :snippet, :html)
        ON DUPLICATE KEY UPDATE subject=VALUES(subject)
        """
    )
    with SessionLocal() as db:
        cur = db.execute(sql, data)
        db.commit()
        return cur.lastrowid


def email_exists(message_id: str) -> bool:
    sql = text("SELECT id FROM qq_email_ingests WHERE gmail_id=:id")
    with SessionLocal() as db:
        res = db.execute(sql, {"id": message_id}).first()
        return res is not None


def find_or_create_strategy(name: str) -> int:
    sql_ins = text(
        """
        INSERT INTO qq_strategies (name)
        VALUES (:name)
        ON DUPLICATE KEY UPDATE name=VALUES(name)
        """
    )
    with SessionLocal() as db:
        cur = db.execute(sql_ins, {"name": name})
        db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        res = db.execute(text("SELECT id FROM qq_strategies WHERE name=:name"), {"name": name}).first()
        return res[0]


def upsert_rebalance(strategy_id: int, rebalance_date, email_ingest_id: int) -> int:
    sql = text(
        """
        INSERT INTO qq_rebalances (strategy_id, rebalance_date, email_ingest_id)
        VALUES (:sid, :rd, :eid)
        ON DUPLICATE KEY UPDATE email_ingest_id=VALUES(email_ingest_id)
        """
    )
    with SessionLocal() as db:
        cur = db.execute(sql, {"sid": strategy_id, "rd": rebalance_date, "eid": email_ingest_id})
        db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        res = db.execute(
            text("SELECT id FROM qq_rebalances WHERE strategy_id=:sid AND rebalance_date=:rd"),
            {"sid": strategy_id, "rd": rebalance_date},
        ).first()
        return res[0]


def upsert_allocation(rebalance_id: int, row: Dict[str, Any]) -> None:
    sql = text(
        """
        INSERT INTO qq_allocations (rebalance_id, ticker, target_weight, current_weight, transaction, rebalance_date)
        VALUES (:rid, :ticker, :target_weight, :current_weight, :transaction, :rebalance_date)
        ON DUPLICATE KEY UPDATE target_weight=VALUES(target_weight), current_weight=VALUES(current_weight)
        """
    )
    data = {"rid": rebalance_id, **row}
    with SessionLocal() as db:
        db.execute(sql, data)
        db.commit()


def mark_rebalance_status(rebalance_id: int, status: str, note: Optional[str] = None) -> None:
    sql = text("UPDATE qq_rebalances SET status=:status, note=:note WHERE id=:id")
    with SessionLocal() as db:
        db.execute(sql, {"status": status, "note": note, "id": rebalance_id})
        db.commit()


def fetch_pending_rebalances() -> List[Dict[str, Any]]:
    sql = text("SELECT * FROM qq_rebalances WHERE status='pending'")
    with SessionLocal() as db:
        res = db.execute(sql).mappings().all()
    return [dict(r) for r in res]


def fetch_allocations(rebalance_id: int) -> List[Dict[str, Any]]:
    sql = text("SELECT * FROM qq_allocations WHERE rebalance_id=:id")
    with SessionLocal() as db:
        res = db.execute(sql, {"id": rebalance_id}).mappings().all()
    return [dict(r) for r in res]


def get_strategy(strategy_id: int) -> Optional[Dict[str, Any]]:
    sql = text("SELECT * FROM qq_strategies WHERE id=:id")
    with SessionLocal() as db:
        res = db.execute(sql, {"id": strategy_id}).mappings().first()
        return dict(res) if res else None


def get_strategies() -> List[Dict[str, Any]]:
    sql = text("SELECT * FROM qq_strategies")
    with SessionLocal() as db:
        res = db.execute(sql).mappings().all()
    return [dict(r) for r in res]


def upsert_strategy(data: Dict[str, Any]) -> int:
    sql = text(
        """
        INSERT INTO qq_strategies (name, capital_usd, price_fill, allow_fractional, rounding_mode, target_sum_tolerance_pct, active)
        VALUES (:name, :capital_usd, :price_fill, :allow_fractional, :rounding_mode, :target_sum_tolerance_pct, :active)
        ON DUPLICATE KEY UPDATE
            capital_usd=VALUES(capital_usd),
            price_fill=VALUES(price_fill),
            allow_fractional=VALUES(allow_fractional),
            rounding_mode=VALUES(rounding_mode),
            target_sum_tolerance_pct=VALUES(target_sum_tolerance_pct),
            active=VALUES(active)
        """
    )
    with SessionLocal() as db:
        cur = db.execute(sql, data)
        db.commit()
        if cur.lastrowid:
            return cur.lastrowid
        res = db.execute(text("SELECT id FROM qq_strategies WHERE name=:name"), {"name": data["name"]}).first()
        return res[0]

# The following helpers are minimal placeholders

def get_nav(strategy_id: int, date_from: Optional[str], date_to: Optional[str]) -> List[Dict[str, Any]]:
    sql = text(
        "SELECT nav_date AS date, nav, cash FROM qq_nav_daily WHERE strategy_id=:sid ORDER BY nav_date"
    )
    with SessionLocal() as db:
        res = db.execute(sql, {"sid": strategy_id}).mappings().all()
    return [dict(r) for r in res]


def get_positions(strategy_id: int, on_date: str) -> List[Dict[str, Any]]:
    sql = text(
        "SELECT * FROM qq_positions_daily WHERE strategy_id=:sid AND position_date=:dt"
    )
    with SessionLocal() as db:
        res = db.execute(sql, {"sid": strategy_id, "dt": on_date}).mappings().all()
    return [dict(r) for r in res]


def get_trades(strategy_id: int, date_from: str, date_to: str) -> List[Dict[str, Any]]:
    sql = text(
        "SELECT * FROM qq_trades WHERE strategy_id=:sid AND trade_date BETWEEN :f AND :t ORDER BY trade_date"
    )
    with SessionLocal() as db:
        res = db.execute(sql, {"sid": strategy_id, "f": date_from, "t": date_to}).mappings().all()
    return [dict(r) for r in res]

