"""Trading mode configuration used by the Signals engine."""

MODE_PROFILES: dict[str, dict] = {
    "swing": {
        "label": "Swing",
        "period": "1y",
        "interval": "1d",
        "lookback_days": 252,
        "chart": {
            "trend_window": 34,
            "momentum_window": 14,
            "volume_window": 20,
        },
        "mindset": {
            "tagline": "Capture multi-day directional moves with disciplined risk.",
            "holding_period": "3-10 sessions",
            "focus": [
                "Align with dominant daily trend",
                "Confirm with momentum bursts",
                "Respect volatility guard-rails",
            ],
        },
        "playbook": [
            "Wait for trend and momentum alignment before sizing up",
            "Scale entries around key moving averages",
            "Fade setups if readiness falls below 40",
        ],
    },
    "intraday": {
        "label": "Intraday",
        "period": "5d",
        "interval": "5m",
        "lookback_days": 10,
        "chart": {
            "trend_window": 20,
            "momentum_window": 8,
            "volume_window": 12,
        },
        "mindset": {
            "tagline": "Stay nimble and respect liquidity pockets.",
            "holding_period": "Minutes-hours",
            "focus": [
                "Open-drive bias and VWAP reaction",
                "Liquidity pockets around overnight levels",
                "Momentum exhaustion and reversal signals",
            ],
        },
        "playbook": [
            "Use VWAP as the north star for bias",
            "Trim risk quickly when volatility spikes",
            "Avoid trades when readiness < 30",
        ],
    },
    "position": {
        "label": "Position",
        "period": "2y",
        "interval": "1d",
        "lookback_days": 504,
        "chart": {
            "trend_window": 55,
            "momentum_window": 21,
            "volume_window": 40,
        },
        "mindset": {
            "tagline": "Ride primary trends with macro confirmation.",
            "holding_period": "Weeks-months",
            "focus": [
                "Confirm trend with macro backdrop",
                "Scale adds on pullbacks into rising averages",
                "Trail stops under weekly structure",
            ],
        },
        "playbook": [
            "Start with 1/2 size until trend proves itself",
            "Review macro regime each weekend",
            "Rotate when readiness diverges for 3 sessions",
        ],
    },
    "crypto": {
        "label": "Crypto",
        "period": "4h",
        "interval": "1d",
        "lookback_days": 504,
        "chart": {
            "trend_window": 55,
            "momentum_window": 21,
            "volume_window": 40,
        },
        "mindset": {
            "tagline": "Crypto is crytpo...good luck and HODL.",
            "holding_period": "HODL",
            "focus": [
                "Confirm trend with macro backdrop",
                "Scale adds on pullbacks into rising averages",
                "Trail stops under weekly structure",
            ],
        },
        "playbook": [
            "Start with 1/2 size until trend proves itself",
            "Review macro regime each weekend",
            "Rotate when readiness diverges for 3 sessions",
        ],
    },
}


__all__ = ["MODE_PROFILES"]
