"""Alert configuration router."""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services.alerts_worker import AlertRule, evaluate_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class ChannelConfig(BaseModel):
    email: Optional[str] = None
    sms: Optional[str] = None
    webpush: Optional[str] = None


class AlertRuleRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    mode: str = Field("swing", description="Trading mode identifier")
    tf: str = Field("1h", description="Timeframe")
    channels: ChannelConfig = Field(default_factory=ChannelConfig)
    rules: Dict[str, float | int | bool] = Field(default_factory=dict)


@router.post("/")
def create_alert(rule: AlertRuleRequest):
    alert_rule = AlertRule(
        symbol=rule.symbol,
        mode=rule.mode,
        timeframe=rule.tf,
        channels=rule.channels.dict(exclude_none=True),
        rules=rule.rules,
    )
    preview = evaluate_alert(alert_rule)
    preview["message"] = (
        f"[{rule.mode.upper()} Signal] {rule.symbol.upper()} ({rule.tf})\n" + preview["summary"]
    )
    return preview
