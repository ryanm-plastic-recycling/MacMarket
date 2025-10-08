import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List

import yfinance as yf
from fastapi import APIRouter, Request, HTTPException, Query, Body
from indicators.haco import compute_haco
from backend.app import alerts as mm_alerts
from backend.app import signals as signal_engine
from backend.app.database import connect_to_db

router = APIRouter()

# --- user resolver (derive the request user id) ---
def _req_user_id(request: Request, explicit: Optional[int] = None) -> int:
    if explicit:
        try:
            return int(explicit)
        except:
            pass
    hdr = request.headers.get("X-User-Id")
    if hdr:
        try:
            return int(hdr)
        except:
            pass
    # TODO: wire real auth; for now default to 1
    return 1
#
# --- UTC helpers (normalize MySQL TIMESTAMP to aware UTC, and get now in UTC) ---
#
def _utc_now():
    return datetime.now(timezone.utc)


def _to_utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _build_signal_preview(
    symbol: str,
    mode: str,
    *,
    min_total_score: float,
    require_trend_pass: bool,
    require_momentum_pass: bool,
) -> dict:
    try:
        data = signal_engine.compute_signals(symbol, mode=mode)
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.exception("Failed to build signal preview for %s", symbol)
        return {"error": str(exc)}

    readiness = data.get("readiness", {})
    score = readiness.get("score", 0.0)
    components = {c.get("id"): c for c in readiness.get("components", []) if isinstance(c, dict)}
    trend = components.get("trend", {})
    momentum = components.get("momentum", {})

    trend_score = float(trend.get("score", 0.0) or 0.0)
    momentum_score = float(momentum.get("score", 0.0) or 0.0)

    passes_total = score >= float(min_total_score)
    passes_trend = (not require_trend_pass) or trend_score >= float(min_total_score)
    passes_momentum = (not require_momentum_pass) or momentum_score >= float(min_total_score)

    return {
        "symbol": symbol.upper(),
        "mode": data.get("mode", mode),
        "readiness_score": score,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "meets_total": passes_total,
        "meets_trend": passes_trend,
        "meets_momentum": passes_momentum,
        "passes": passes_total and passes_trend and passes_momentum,
        "panels": data.get("panels", []),
        "entries": data.get("entries", []),
        "exits": data.get("exits", {}),
        "criteria": {
            "min_total_score": float(min_total_score),
            "require_trend_pass": bool(require_trend_pass),
            "require_momentum_pass": bool(require_momentum_pass),
        },
    }


async def _alerts_worker() -> None:  # pragma: no cover - background task
    while True:
        try:
            conn = connect_to_db()
            cur = conn.cursor(dictionary=True)
            # Iterate per-alert rows
            cur.execute(
                "SELECT id, user_id, symbol, strategy, frequency, email, sms, is_enabled, email_template, sms_template FROM user_alerts WHERE is_enabled=1"
            )
            alerts = cur.fetchall() or []
            for a in alerts:
                alert_id = a["id"]
                sym = a["symbol"]
                freq = (a["frequency"] or "15m").lower()
                # throttle by alert_state
                cur.execute(
                    "SELECT last_state, last_checked FROM alert_state WHERE alert_id=%s",
                    (alert_id,),
                )
                st = cur.fetchone() or {"last_state": None, "last_checked": None}
                secs = {"5m": 300, "15m": 900, "1h": 3600, "1d": 86400}.get(freq, 900)
                if st["last_checked"] is not None:
                    dt = _to_utc(st["last_checked"])
                    if dt is not None:
                        if (_utc_now() - dt).total_seconds() < secs:
                            continue
                # pull candles for freq
                interval, period = (
                    ("5m", "7d")
                    if freq == "5m"
                    else ("15m", "60d")
                    if freq == "15m"
                    else ("1h", "730d")
                    if freq == "1h"
                    else ("1d", "3y")
                )
                df = (
                    yf.download(
                        sym,
                        period=period,
                        interval=interval,
                        auto_adjust=False,
                        progress=False,
                    ).dropna()
                )
                if df.empty:
                    cur.execute(
                        "REPLACE INTO alert_state (alert_id,last_state,last_checked) VALUES (%s,%s,UTC_TIMESTAMP())",
                        (alert_id, st["last_state"]),
                    )
                    conn.commit()
                    continue
                candles = [
                    {
                        "time": int(ts.to_pydatetime().timestamp()),
                        "o": float(row.at["Open"]),
                        "h": float(row.at["High"]),
                        "l": float(row.at["Low"]),
                        "c": float(row.at["Close"]),
                    }
                    for ts, row in df.iterrows()
                ]
                # compute strategy state (HACO or MACD)
                if (a["strategy"] or "HACO") == "HACO":
                    out = compute_haco(candles)
                    ser = out.get("series") or []
                    if not ser:
                        continue
                    last = ser[-1]
                    state_now = "UP" if bool(last.get("state")) else "DOWN"
                    reason = last.get("reason", "") if isinstance(last, dict) else ""
                    px = float(last.get("c", 0.0))
                    extra = {}
                else:
                    # ---- MACD implementation (12,26,9) on closes — ALERT ONLY ON CROSSOVER ----
                    closes = [float(row.at["Close"]) for _, row in df.iterrows()]
                    if len(closes) < 35:
                        cur.execute("REPLACE INTO alert_state (alert_id,last_state,last_checked) VALUES (%s,%s,UTC_TIMESTAMP())",
                                    (alert_id, st["last_state"]))
                        conn.commit(); continue
                    def ema_series(vals, length):
                        alpha = 2.0/(length+1.0)
                        out=[vals[0]]
                        for v in vals[1:]:
                            out.append(alpha*v + (1.0-alpha)*out[-1])
                        return out
                    ema12  = ema_series(closes, 12)
                    ema26  = ema_series(closes, 26)
                    macd   = [ema12[i] - ema26[i] for i in range(len(closes))]
                    signal = ema_series(macd, 9)
                    hist   = [macd[i] - signal[i] for i in range(len(macd))]
                    m_prev, s_prev = macd[-2], signal[-2]
                    m, s, h        = macd[-1],  signal[-1], hist[-1]
                    cross_up   = (m_prev <= s_prev) and (m > s)
                    cross_down = (m_prev >= s_prev) and (m < s)
                    if not (cross_up or cross_down):
                        # No crossover: just advance throttle window; do NOT send, do NOT flip last_state.
                        cur.execute("REPLACE INTO alert_state (alert_id,last_state,last_checked) VALUES (%s,%s,UTC_TIMESTAMP())",
                                    (alert_id, st["last_state"]))
                        conn.commit(); continue
                    # Crossover happened on this bar -> send
                    state_now = "UP" if cross_up else "DOWN"
                    cross_lbl = "BULLISH_CROSS" if cross_up else "BEARISH_CROSS"
                    reason = f"MACD {('▲' if cross_up else '▼')} cross: {m:.2f} vs {s:.2f} (hist {h:.2f})"
                    px = closes[-1]
                    extra = {"macd": f"{m:.2f}", "signal": f"{s:.2f}", "hist": f"{h:.2f}", "cross": cross_lbl}
                # on change -> notify
                if state_now is not None and state_now != st["last_state"]:
                    ctx = {
                        "symbol": sym,
                        "strategy": a["strategy"],
                        "frequency": a["frequency"],
                        "state": state_now,
                        "reason": reason,
                        "ts": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "price": f"{px:.2f}",
                    }
                    ctx.update(extra)
                    def render(tpl: str | None, ctx: dict) -> str:
                        if not tpl:
                            return f"{sym} {state_now} ({a['strategy']} {a['frequency']})"
                        msg = tpl
                        for k, v in ctx.items():
                            msg = msg.replace("{{" + k + "}}", str(v))
                        return msg
                    subj = f"{sym} {state_now} • {a['strategy']} {a['frequency']}"
                    body = render(a.get("email_template"), ctx)
                    sms = render(a.get("sms_template"), ctx)
                    if a.get("email"):
                        mm_alerts.send_email(a["email"], subj, body)
                    if a.get("sms"):
                        mm_alerts.send_sms(a["sms"], sms)
                # upsert state (HACO on flip, MACD on crossover)
                cur.execute("REPLACE INTO alert_state (alert_id,last_state,last_checked) VALUES (%s,%s,UTC_TIMESTAMP())",
                            (alert_id, state_now))
                conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:  # pragma: no cover - logging only
            logging.error("alerts worker error: %s", exc)
        await asyncio.sleep(60)

#
# --- Back-compat alias routes for legacy frontends calling /api/alerts/me ---
#     GET  /api/alerts/me     -> list alerts for a user
#     POST /api/alerts/me     -> update if 'id' present; else bulk-create via 'symbols' or single create
#
@router.get("/api/alerts/me")
def list_alerts_me(request: Request, userId: int | None = Query(None, alias="userId")):
    uid = _req_user_id(request, userId)
    conn = connect_to_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_alerts WHERE user_id=%s ORDER BY symbol,id", (uid,))
    rows = cur.fetchall() or []
    cur.close(); conn.close()
    return rows


@router.post("/api/alerts/me")
def upsert_alerts_me(request: Request, payload: dict = Body(...), userId: int | None = Query(None, alias="userId")):
    """Back-compat: create/update alerts using the old /me endpoint."""
    uid = _req_user_id(request, payload.get("user_id") or userId)
    conn = connect_to_db(); cur = conn.cursor(dictionary=True)
    # Update path when an 'id' is provided
    if "id" in payload:
        fields = ["symbol","strategy","frequency","email","sms","email_template","sms_template","is_enabled"]
        sets, vals = [], []
        for f in fields:
            if f in payload:
                sets.append(f"{f}=%s"); vals.append(payload[f])
        if sets:
            vals.append(int(payload["id"]))
            cur2 = conn.cursor()
            cur2.execute(f"UPDATE user_alerts SET {', '.join(sets)}, updated_at=UTC_TIMESTAMP() WHERE id=%s", tuple(vals))
            conn.commit(); cur2.close()
        cur.close(); conn.close()
        return {"ok": True, "updated": payload["id"]}
    # Bulk create path with 'symbols'
    symbols = payload.get("symbols")
    if isinstance(symbols, str):
        symbols = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if isinstance(symbols, list) and symbols:
        created: List[int] = []
        for sym in symbols:
            cur2 = conn.cursor()
            cur2.execute(
                """
              INSERT INTO user_alerts (user_id,symbol,strategy,frequency,email,sms,is_enabled)
              VALUES (%s,%s,%s,%s,%s,%s,1)
            """,
                (
                    uid,
                    sym,
                    (payload.get("strategy") or "HACO"),
                    (payload.get("frequency") or "1h"),
                    payload.get("email"),
                    payload.get("sms"),
                ),
            )
            created.append(cur2.lastrowid); conn.commit(); cur2.close()
        cur.close(); conn.close()
        return {"ok": True, "created": created}
    # Single create path
    cur2 = conn.cursor()
    cur2.execute(
        """
      INSERT INTO user_alerts (user_id,symbol,strategy,frequency,email,sms,is_enabled,email_template,sms_template)
      VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s)
    """,
        (
            uid,
      str(payload.get("symbol", "")).strip().upper(),
            (payload.get("strategy") or "HACO"),
            (payload.get("frequency") or "1h"),
            payload.get("email"),
            payload.get("sms"),
            payload.get("email_template"),
            payload.get("sms_template"),
        ),
    )
    new_id = cur2.lastrowid; conn.commit(); cur2.close(); cur.close(); conn.close()
    return {"ok": True, "created": [new_id]}


@router.on_event("startup")
async def _startup() -> None:  # pragma: no cover
    asyncio.create_task(_alerts_worker())


# --------- CRUD: per-alert rows -------------
@router.get("/api/alerts")
def list_alerts(request: Request, userId: Optional[int] = Query(None, alias="userId")):
    uid = _req_user_id(request, userId)
    conn = connect_to_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM user_alerts WHERE user_id=%s ORDER BY symbol,id", (uid,))
    rows = cur.fetchall() or []
    cur.close(); conn.close()
    return rows


@router.post("/api/alerts")
def create_alert(request: Request, payload: dict = Body(...)):
    uid = _req_user_id(request, payload.get("user_id"))
    req = {k: payload.get(k) for k in ["symbol","strategy","frequency","email","sms","email_template","sms_template","is_enabled"]}
    if not req["symbol"]:
        raise HTTPException(status_code=400, detail="user_id and symbol required")
    symbol = str(req["symbol"]).strip().upper()
    mode = (payload.get("mode") or "swing").lower()
    min_total_score = float(payload.get("min_total_score", 55))
    require_trend = bool(payload.get("require_trend_pass"))
    require_momentum = bool(payload.get("require_momentum_pass"))
    preview_requested = bool(
        payload.get("preview")
        or payload.get("preview_only")
        or request.query_params.get("preview")
    )
    preview = None
    if preview_requested:
        preview = _build_signal_preview(
            symbol,
            mode,
            min_total_score=min_total_score,
            require_trend_pass=require_trend,
            require_momentum_pass=require_momentum,
        )
        if payload.get("preview_only"):
            return {"preview": preview}
    conn = connect_to_db(); cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_alerts (user_id,symbol,strategy,frequency,email,sms,email_template,sms_template,is_enabled)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,1))
    """,
        (uid, symbol, req.get("strategy","HACO"), req.get("frequency","1h"),
         req.get("email"), req.get("sms"), req.get("email_template"), req.get("sms_template"), req.get("is_enabled"))
    )
    alert_id = cur.lastrowid
    conn.commit(); cur.close(); conn.close()
    response = {"id": alert_id}
    if preview:
        response["preview"] = preview
    return response


@router.put("/api/alerts/{alert_id}")
def update_alert(request: Request, alert_id: int, payload: dict = Body(...)):
    uid = _req_user_id(request, payload.get("user_id"))
    # verify ownership
    conn = connect_to_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM user_alerts WHERE id=%s", (alert_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="alert_not_found")
    if int(row["user_id"]) != int(uid):
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="forbidden")
    fields = ["symbol","strategy","frequency","email","sms","email_template","sms_template","is_enabled"]
    sets = []; vals = []
    for f in fields:
        if f in payload:
            sets.append(f"{f}=%s"); vals.append(payload[f])
    if not sets:
        raise HTTPException(status_code=400, detail="no fields")
    vals.append(alert_id)
    cur2 = conn.cursor()
    cur2.execute(f"UPDATE user_alerts SET {', '.join(sets)}, updated_at=UTC_TIMESTAMP() WHERE id=%s", tuple(vals))
    conn.commit(); cur2.close(); cur.close(); conn.close()
    return {"ok": True}


@router.delete("/api/alerts/{alert_id}")
def delete_alert(request: Request, alert_id: int):
    uid = _req_user_id(request)
    conn = connect_to_db(); cur = conn.cursor(dictionary=True)
    # verify ownership
    cur.execute("SELECT user_id FROM user_alerts WHERE id=%s", (alert_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="alert_not_found")
    if int(row["user_id"]) != int(uid):
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="forbidden")
    cur2 = conn.cursor()
    cur2.execute("DELETE FROM user_alerts WHERE id=%s", (alert_id,))
    conn.commit(); 
    cur2.close(); cur.close(); conn.close()
    return {"ok": True}
