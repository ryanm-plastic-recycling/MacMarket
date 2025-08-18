import time
from datetime import datetime
from backend.app.database import SessionLocal
from backend.app import crud, alerts, schemas
from indicators.haco import compute_haco
from services.data import get_candles


def check_alerts():
    db = SessionLocal()
    try:
        for alert in crud.get_all_haco_alerts(db):
            now = datetime.utcnow()
            if alert.last_checked and (now - alert.last_checked).total_seconds() < alert.frequency * 60:
                continue
            candles = get_candles(alert.symbol, "Day", 500)
            if not candles:
                continue
            data = compute_haco(candles)
            if not data.get("series"):
                continue
            state = data["series"][-1].get("state")
            if state != alert.last_state:
                msg = f"HACO state for {alert.symbol} changed to {state}"
                if alert.email:
                    alerts.send_email(alert.email, f"{alert.symbol} HACO Alert", msg)
                if alert.sms:
                    alerts.send_sms(alert.sms, msg)
            crud.update_haco_alert(db, alert, schemas.HacoAlertUpdate(last_state=state, last_checked=now))
    finally:
        db.close()


def main():
    while True:
        check_alerts()
        time.sleep(60)


if __name__ == "__main__":
    main()
