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
    username: str
    is_admin: bool = False
    email: Optional[EmailStr] = None

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    username: str
    password: str


class PasswordUpdate(BaseModel):
    password: str


class TickerList(BaseModel):
    tickers: list[str]
