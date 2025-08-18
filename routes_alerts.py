import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from backend.app.database import connect_to_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In lieu of real auth, always use user 1

def _user_id(request: Request) -> int:  # pragma: no cover - simple stub
    return 1


@router.get("/me")
async def get_me(request: Request) -> Dict[str, Any]:
    uid = _user_id(request)
    conn = connect_to_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT email, sms, frequency, strategy FROM user_alert_settings WHERE user_id=%s LIMIT 1",
        (uid,),
    )
    pref = cur.fetchone()
    cur.execute(
        "SELECT symbol FROM user_alert_symbols WHERE user_id=%s ORDER BY symbol",
        (uid,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {
        "strategy": (pref["strategy"] if pref else "HACO"),
        "email": (pref["email"] if pref else ""),
        "sms": (pref["sms"] if pref else ""),
        "frequency": (pref["frequency"] if pref else "15m"),
        "symbols": [r["symbol"] for r in rows] if rows else [],
    }


@router.post("/me")
async def set_me(request: Request) -> Dict[str, Any]:
    uid = _user_id(request)
    body = await request.json()
    strategy = body.get("strategy") or "HACO"
    email = (body.get("email") or "").strip()
    sms = (body.get("sms") or "").strip()
    freq = body.get("frequency") or "15m"
    symbols: List[str] = [str(s).upper().strip() for s in (body.get("symbols") or []) if s]

    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO user_alert_settings (user_id,email,sms,frequency,strategy)
           VALUES (%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE email=VALUES(email), sms=VALUES(sms),
                                   frequency=VALUES(frequency), strategy=VALUES(strategy)""",
        (uid, email, sms, freq, strategy),
    )
    cur.execute("DELETE FROM user_alert_symbols WHERE user_id=%s", (uid,))
    if symbols:
        cur.executemany(
            "INSERT INTO user_alert_symbols (user_id,symbol) VALUES (%s,%s)",
            [(uid, s) for s in symbols],
        )
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


@router.post("/test")
async def test_alerts() -> Dict[str, Any]:
    return {"ok": True}


# --- Background worker ----------------------------------------------------

async def _alerts_worker() -> None:  # pragma: no cover - background task
    while True:
        try:
            conn = connect_to_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT user_id, strategy, frequency FROM user_alert_settings"
            )
            rows = cur.fetchall() or []
            cur.close()
            conn.close()
            for r in rows:
                logging.info(
                    "[alerts] would run %s for user %s at %s", r["strategy"], r["user_id"], r["frequency"]
                )
        except Exception as exc:  # pragma: no cover - logging only
            logging.error("alerts worker error: %s", exc)
        await asyncio.sleep(60)


@router.on_event("startup")
async def _startup() -> None:  # pragma: no cover
    asyncio.create_task(_alerts_worker())
