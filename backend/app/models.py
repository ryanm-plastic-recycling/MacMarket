from sqlalchemy import Column, Integer, String, Boolean, Enum, DECIMAL, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from .database import Base
import enum

class AlertType(str, enum.Enum):
    email = "email"
    sms = "sms"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

    alerts = relationship("AlertPreference", back_populates="user")

class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False)

    user = relationship("User", back_populates="alerts")
