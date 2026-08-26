"""Holt Linear Exponential Smoothing forecast."""
from __future__ import annotations

import warnings

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import annual_grid, fill_flat


def holt_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast using Holt's additive-trend Exponential Smoothing.

    Uncertainty bands grow with sqrt(steps) from in-sample residual std,
    approximating the theoretical prediction interval for a smoothed trend.
    """
    from scipy.stats import norm as _norm
    z = float(_norm.ppf(1 - (1 - ci) / 2))

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    result = RateResult(transect_id=series.transect_id, method="holt")

    if len(years) < 3:
        fill_flat(result, last_year, last_dist, horizon_years)
        return result

    grid_years, grid_d = annual_grid(years, d)
    if len(grid_d) < 3:
        fill_flat(result, last_year, last_dist, horizon_years)
        return result

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(
                grid_d, trend="add", initialization_method="estimated",
            ).fit(optimized=True)
        fc = fit.forecast(horizon_years)
        resid_std = (float(np.std(fit.resid))
                     if len(fit.resid) > 1
                     else abs(float(np.mean(grid_d))) * 0.05 + 1.0)
        fut_years = [last_year + i for i in range(1, horizon_years + 1)]
        result.forecast_years = fut_years
        result.forecast_distances = fc.tolist()
        result.forecast_lower = [v - z * resid_std * np.sqrt(i) for i, v in enumerate(fc, 1)]
        result.forecast_upper = [v + z * resid_std * np.sqrt(i) for i, v in enumerate(fc, 1)]
    except Exception:
        fill_flat(result, last_year, last_dist, horizon_years)
    return result
