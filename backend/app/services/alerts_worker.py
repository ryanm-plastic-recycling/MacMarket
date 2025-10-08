"""Alert preview and dispatch helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..services.signals_engine import compute_signals


@dataclass
class AlertRule:
    symbol: str
    mode: str
    timeframe: str
    channels: Dict[str, str]
    rules: Dict[str, bool | float | int]


def evaluate_alert(rule: AlertRule) -> Dict:
    payload = compute_signals(rule.symbol, rule.mode)
    readiness = payload.get("readiness", 0)
    panels = {p["id"]: p for p in payload.get("panels", [])}
    trend_pass = panels.get("trend", {}).get("status") == "PASS"
    momentum_pass = panels.get("momentum", {}).get("status") == "PASS"

    requirements_met = True
    min_score = rule.rules.get("min_total_score")
    if rule.rules.get("require_trend_pass") and not trend_pass:
        requirements_met = False
    if rule.rules.get("require_momentum_pass") and not momentum_pass:
        requirements_met = False
    if min_score is not None and readiness < float(min_score):
        requirements_met = False

    trend_panel = panels.get("trend")
    momentum_panel = panels.get("momentum")
    volatility_panel = panels.get("volatility")
    volume_panel = panels.get("volume")
    stops_panel = panels.get("stops")

    summary_lines = [
        f"Trend: {trend_panel['status']} ({trend_panel['reason']})" if trend_panel else "Trend: n/a",
        f"Momentum: {momentum_panel['status']} ({momentum_panel['reason']})" if momentum_panel else "Momentum: n/a",
        f"Volatility: {volatility_panel['status']} ({volatility_panel['reason']})" if volatility_panel else "Volatility: n/a",
        f"Volume: {volume_panel['status']} ({volume_panel['reason']})" if volume_panel else "Volume: n/a",
    ]
    if stops_panel:
        summary_lines.append(f"Stops: {stops_panel['reason']}")

    preview = {
        "triggered": requirements_met,
        "readiness": readiness,
        "panels": payload["panels"],
        "summary": "\n".join(summary_lines),
        "exits": payload.get("exits", {}),
    }
    return preview
