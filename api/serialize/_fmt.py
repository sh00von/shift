"""Shared formatting helper."""
from __future__ import annotations
import math


def fmt(v, d: int = 2) -> str:
    """Format a numeric value to `d` decimal places, or '—' if missing/NaN."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)
