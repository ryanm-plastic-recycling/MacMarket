"""Simple risk management utilities.

This module provides helpers to fetch user positions, calculate portfolio exposure,
and obtain LLM-based suggestions on potential risk actions.
"""

from typing import List
from sqlalchemy.orm import Session
from . import models
import os

try:
    import openai  # optional dependency
except Exception:
    openai = None


def get_positions(db: Session, user_id: int) -> List[models.Position]:
    """Return all positions for a user."""
    return db.query(models.Position).filter(models.Position.user_id == user_id).all()


def calculate_exposure(positions: List[models.Position]) -> float:
    """Return total portfolio exposure based on position size * price."""
    return float(sum(abs(p.quantity) * float(p.price) for p in positions))


def llm_suggestion(summary: str) -> str:
    """Return an LLM-generated suggestion based on the portfolio summary."""
    if openai and os.getenv("OPENAI_API_KEY"):
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": summary}],
            )
            return resp.choices[0].message["content"].strip()
        except Exception:
            pass
    return "LLM suggestion unavailable"
