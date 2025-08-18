from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime
from . import models

class AlertType(str, Enum):
    email = "email"
    sms = "sms"

class AlertPreferenceBase(BaseModel):
    alert_type: AlertType
    enabled: bool = True
    threshold: Optional[float] = None

class AlertPreferenceCreate(AlertPreferenceBase):
    pass

class AlertPreferenceUpdate(AlertPreferenceBase):
    pass

class AlertPreference(AlertPreferenceBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True
        from_attributes = True


class HacoAlertBase(BaseModel):
    symbol: str
    frequency: int
    email: Optional[EmailStr] = None
    sms: Optional[str] = None
    last_state: Optional[str] = None
    last_checked: Optional[datetime] = None


class HacoAlertCreate(HacoAlertBase):
    pass


class HacoAlertUpdate(BaseModel):
    symbol: Optional[str] = None
    frequency: Optional[int] = None
    email: Optional[EmailStr] = None
    sms: Optional[str] = None
    last_state: Optional[str] = None
    last_checked: Optional[datetime] = None


class HacoAlert(HacoAlertBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True
        from_attributes = True

class User(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    email: Optional[EmailStr] = None

    class Config:
        orm_mode = True
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str
    captcha_token: Optional[str] = None
    otp: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    captcha_token: str
    email: Optional[EmailStr] = None


class PasswordUpdate(BaseModel):
    password: str


class UsernameUpdate(BaseModel):
    username: str


class OtpUpdate(BaseModel):
    otp_enabled: bool


class TickerList(BaseModel):
    tickers: list[str]


class EmailUpdate(BaseModel):
    email: EmailStr

class JournalEntryBase(BaseModel):
    symbol: str
    action: models.ActionType
    quantity: float
    price: float
    rationale: Optional[str] = None


class JournalEntryCreate(JournalEntryBase):
    pass


class JournalEntryUpdate(BaseModel):
    """Update fields for an existing journal entry."""
    symbol: Optional[str] = None
    action: Optional[models.ActionType] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    rationale: Optional[str] = None


class JournalEntry(JournalEntryBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True
        from_attributes = True


class Recommendation(BaseModel):
    symbol: str
    action: str
    exit: Optional[float] = None
    probability: float


class JournalEntryWithRec(JournalEntry):
    """A journal entry with an optional recommendation."""

    recommendation: Optional[Recommendation] = None

class Position(BaseModel):
    id: int | None = None
    user_id: int | None = None
    symbol: str
    quantity: float
    price: float
    created_at: Optional[datetime] | None = None

    class Config:
        orm_mode = True
        from_attributes = True


class BacktestRun(BaseModel):
    id: int | None = None
    user_id: int | None = None
    symbol: str
    start_date: str
    end_date: str
    metrics: dict
    created_at: datetime | None = None

    class Config:
        orm_mode = True
        from_attributes = True
