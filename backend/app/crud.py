from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas
import hashlib

# User helper functions

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_or_create_user(db: Session, username: str, password: str, email: Optional[str] = None) -> models.User:
    user = get_user_by_username(db, username)
    if not user:
        user = models.User(username=username, password_hash=_hash(password), email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.password_hash != _hash(password):
            raise ValueError("Invalid credentials")
    return user


def set_user_password(db: Session, user_id: int, password: str):
    user = get_user(db, user_id)
    if user:
        user.password_hash = _hash(password)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def set_admin_status(db: Session, user_id: int, is_admin: bool):
    user = get_user(db, user_id)
    if user:
        user.is_admin = is_admin
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()

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
