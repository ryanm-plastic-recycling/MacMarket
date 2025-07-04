from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

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

class User(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    email: EmailStr


class TickerList(BaseModel):
    tickers: list[str]
