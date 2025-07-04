from sqlalchemy import Column, Integer, String, Boolean, Enum, DECIMAL, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import relationship
from .database import Base
import enum

class AlertType(str, enum.Enum):
    email = "email"
    sms = "sms"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    email = Column(String(255), unique=True, nullable=True)
    totp_secret = Column(String(32), nullable=False)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )

    alerts = relationship("AlertPreference", back_populates="user")

class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )

    user = relationship("User", back_populates="alerts")


class UserTicker(Base):
    __tablename__ = "user_tickers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(10), nullable=False)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
