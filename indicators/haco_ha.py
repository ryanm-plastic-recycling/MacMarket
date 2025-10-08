"""Approximate HACO helper used by the Codex Signals UI.

This version keeps the historic behaviour of ``indicators.haco`` but exposes a
slightly simplified interface geared towards quickly producing chart payloads
with Heikin-Ashi candles.
"""

from __future__ import annotations

from typing import Iterable

from .common import heikin_ashi


def project(candles: Iterable[dict[str, float]]) -> list[dict[str, float]]:
    """Return Heikin-Ashi candles derived from ``candles``."""

    return heikin_ashi(candles)


__all__ = ["project"]
