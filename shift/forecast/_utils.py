"""Shared utilities for all forecast modules."""
from __future__ import annotations

import numpy as np
from shift.models import RateResult


def annual_grid(
    years: np.ndarray, distances: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate survey data onto an annual integer grid."""
    y0, y1 = int(np.floor(years[0])), int(np.ceil(years[-1]))
    grid = np.arange(y0, y1 + 1, dtype=float)
    interp = np.interp(grid, years, distances)
    return grid, interp


def fill_flat(
    result: RateResult, last_year: float, last_dist: float, horizon: int
) -> None:
    """Fill forecast fields with a flat (no-change) projection."""
    result.forecast_years = [last_year + i for i in range(1, horizon + 1)]
    result.forecast_distances = [last_dist] * horizon
    result.forecast_lower = [last_dist] * horizon
    result.forecast_upper = [last_dist] * horizon
