"""Trading mode configuration used by the Signals engine."""

MODE_PROFILES: dict[str, dict] = {
    "day": {
        "label": "Day",
        "period": "5d",           # intraday history window
        "interval": "5m",         # or "15m" if you want fewer bars
        "lookback_days": 10,
        "chart": {"trend_window": 20, "momentum_window": 8, "volume_window": 12},
        "mindset": {
            "tagline": "Stay nimble and respect liquidity pockets.",
            "holding_period": "Minutes–hours",
            "focus": ["VWAP reaction", "Liquidity around overnight levels", "Avoid chop"],
        },
        "playbook": ["Use VWAP for bias", "Trim risk fast on spikes", "Skip when readiness < 30"],
    },
    "swing": {
        "label": "Swing",
        "period": "1y",
        "interval": "1d",
        "lookback_days": 252,
        "chart": {"trend_window": 34, "momentum_window": 14, "volume_window": 20},
        "mindset": {
            "tagline": "Capture multi-day directional moves with disciplined risk.",
            "holding_period": "3–10 sessions",
            "focus": ["Align with daily trend", "Confirm momentum bursts", "Respect volatility rails"],
        },
        "playbook": ["Wait for alignment", "Scale near moving averages", "Fade if readiness < 40"],
    },
    "position": {
        "label": "Position",
        "period": "2y",
        "interval": "1d",
        "lookback_days": 504,
        "chart": {"trend_window": 55, "momentum_window": 21, "volume_window": 40},
        "mindset": {
            "tagline": "Ride primary trends with macro confirmation.",
            "holding_period": "Weeks–months",
            "focus": ["Confirm macro backdrop", "Add on pullbacks", "Trail under weekly structure"],
        },
        "playbook": ["Start half size", "Weekly macro review", "Rotate after prolonged divergence"],
    },
    "crypto": {
        "label": "Crypto",
        "period": "365d",         # one year
        "interval": "60m",        # yfinance-supported intraday; later we can resample 4h
        "lookback_days": 365,
        "chart": {"trend_window": 55, "momentum_window": 21, "volume_window": 40},
        "mindset": {
            "tagline": "24/7 market – mind liquidity and weekend behavior.",
            "holding_period": "Multi-day to multi-week",
            "focus": ["Watch funding/liquidity", "Respect weekend variance", "Use wider ATR stops"],
        },
        "playbook": ["Mind overnight/weekend risk", "Wider stops (ATR×2–2.5)", "Size smaller on breakouts"],
    },
}

__all__ = ["MODE_PROFILES"]
