from sqlalchemy.orm import Session
from typing import List
from . import models, schemas

# User helper functions

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_or_create_user(db: Session, email: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# AlertPreference CRUD

def get_alert(db: Session, user_id: int, alert_id: int):
    return (
        db.query(models.AlertPreference)
        .filter(models.AlertPreference.user_id == user_id, models.AlertPreference.id == alert_id)
        .first()
    )

def get_alerts(db: Session, user_id: int):
    return db.query(models.AlertPreference).filter(models.AlertPreference.user_id == user_id).all()

def create_alert(db: Session, user_id: int, alert: schemas.AlertPreferenceCreate):
    db_alert = models.AlertPreference(user_id=user_id, **alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def update_alert(db: Session, alert_obj: models.AlertPreference, alert: schemas.AlertPreferenceUpdate):
    for field, value in alert.dict(exclude_unset=True).items():
        setattr(alert_obj, field, value)
    db.add(alert_obj)
    db.commit()
    db.refresh(alert_obj)
    return alert_obj

def delete_alert(db: Session, alert_obj: models.AlertPreference):
    db.delete(alert_obj)
    db.commit()


# User ticker helpers
def get_tickers(db: Session, user_id: int):
    return db.query(models.UserTicker).filter(models.UserTicker.user_id == user_id).all()


def set_user_tickers(db: Session, user_id: int, tickers: List[str]):
    db.query(models.UserTicker).filter(models.UserTicker.user_id == user_id).delete()
    for sym in tickers:
        db.add(models.UserTicker(user_id=user_id, symbol=sym))
    db.commit()
