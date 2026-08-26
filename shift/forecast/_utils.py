"""Shared utilities for all forecast modules."""
from __future__ import annotations

import numpy as np
from shift.models import RateResult, TransectSeries


def annual_grid(
    years: np.ndarray, distances: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate survey data onto an annual integer grid."""
    y0, y1 = int(np.floor(years[0])), int(np.ceil(years[-1]))
    grid = np.arange(y0, y1 + 1, dtype=float)
    interp = np.interp(grid, years, distances)
    return grid, interp


def strip_outliers(series: TransectSeries, k: float = 1.5) -> TransectSeries:
    """Return a copy of *series* with MAD-based outlier positions removed.

    Uses the residuals from a linear fit (not raw distances) so a genuine
    long-term trend is not mistaken for an outlier. Points whose residual
    exceeds k × MAD are dropped. The original series is returned unchanged
    when fewer than 4 surveys remain after filtering (not enough to be useful).
    """
    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)

    if len(years) < 4:
        return series

    slope, intercept = np.polyfit(years, d, 1)
    resid = d - (slope * years + intercept)
    mad = float(np.median(np.abs(resid - np.median(resid))))

    if mad == 0.0:
        return series

    mask = np.abs(resid - np.median(resid)) <= k * mad
    if mask.sum() < 4:
        return series

    from dataclasses import replace
    return replace(
        series,
        dates=[dt for dt, m in zip(series.dates, mask) if m],
        distances=[dist for dist, m in zip(series.distances, mask) if m],
        uncertainties=[u for u, m in zip(series.uncertainties, mask) if m],
    )


def fill_flat(
    result: RateResult, last_year: float, last_dist: float, horizon: int
) -> None:
    """Fill forecast fields with a flat (no-change) projection."""
    result.forecast_years = [last_year + i for i in range(1, horizon + 1)]
    result.forecast_distances = [last_dist] * horizon
    result.forecast_lower = [last_dist] * horizon
    result.forecast_upper = [last_dist] * horizon
