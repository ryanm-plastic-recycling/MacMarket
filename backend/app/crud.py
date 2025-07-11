from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas
from datetime import datetime
import hashlib
import json

# User helper functions

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(db: Session, username: str, password: str, email: Optional[str] = None) -> models.User:
    """Create a new user. Raises ValueError if username already exists."""
    if get_user_by_username(db, username):
        raise ValueError("User already exists")
    import pyotp
    secret = pyotp.random_base32()
    user = models.User(
        username=username,
        password_hash=_hash(password),
        email=email,
        totp_secret=secret,
        otp_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> models.User:
    """Return user if credentials are valid, otherwise raise ValueError."""
    user = get_user_by_username(db, username)
    if not user or user.password_hash != _hash(password):
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


def set_user_email(db: Session, user_id: int, email: str):
    """Update a user's email and return the updated user."""
    user = get_user(db, user_id)
    if user:
        user.email = email
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def set_username(db: Session, user_id: int, username: str):
    """Update a user's username and return the updated user."""
    if get_user_by_username(db, username):
        raise ValueError("User already exists")
    user = get_user(db, user_id)
    if user:
        user.username = username
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def set_otp_enabled(db: Session, user_id: int, enabled: bool):
    """Enable or disable OTP for the user."""
    user = get_user(db, user_id)
    if user:
        user.otp_enabled = enabled
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_last_login(db: Session, user_id: int):
    """Update the last_logged_in timestamp for the user."""
    user = get_user(db, user_id)
    if user:
        user.last_logged_in = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# Journal helpers

def create_journal_entry(
    db: Session,
    user_id: int,
    symbol: str,
    action: models.ActionType,
    quantity: float,
    price: float,
    rationale: str | None = None,
) -> models.JournalEntry:
    entry = models.JournalEntry(
        user_id=user_id,
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        rationale=rationale,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_journal_entries(db: Session, user_id: int) -> List[models.JournalEntry]:
    return db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).all()


def get_journal_entry(db: Session, user_id: int, entry_id: int) -> models.JournalEntry | None:
    """Return a single journal entry for the user."""
    return (
        db.query(models.JournalEntry)
        .filter(models.JournalEntry.user_id == user_id, models.JournalEntry.id == entry_id)
        .first()
    )


def update_journal_entry(
    db: Session, entry_obj: models.JournalEntry, update: schemas.JournalEntryUpdate
) -> models.JournalEntry:
    for field, value in update.dict(exclude_unset=True).items():
        setattr(entry_obj, field, value)
    db.add(entry_obj)
    db.commit()
    db.refresh(entry_obj)
    return entry_obj


def delete_journal_entry(db: Session, entry_obj: models.JournalEntry) -> None:
    db.delete(entry_obj)
    db.commit()

# Backtest helpers

def create_backtest_run(
    db: Session,
    symbol: str,
    start_date: str,
    end_date: str,
    metrics: dict,
    user_id: int | None = None,
) -> models.BacktestRun:
    run = models.BacktestRun(
        user_id=user_id,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        metrics=json.dumps(metrics),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_backtest_runs(db: Session, user_id: int | None = None) -> list[models.BacktestRun]:
    q = db.query(models.BacktestRun)
    if user_id is not None:
        q = q.filter(models.BacktestRun.user_id == user_id)
    return q.order_by(models.BacktestRun.created_at.desc()).all()
