"""ARIMA(1,1,1) forecast with a deterministic linear trend component."""
from __future__ import annotations

import warnings

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import annual_grid, fill_flat, strip_outliers


def arima_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast using ARIMA(1,1,1) with trend='t'.

    Uses statsmodels ARIMA with a deterministic linear time trend baked in,
    which guarantees the forecast changes proportionally with the horizon.
    pmdarima's auto-selection on sparse coastal data routinely picks
    ARIMA(0,1,0) with zero drift, producing a flat line for any horizon.
    """
    from scipy.stats import norm as _norm

    series = strip_outliers(series)
    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    result = RateResult(transect_id=series.transect_id, method="arima")

    if len(years) < 3:
        fill_flat(result, last_year, last_dist, horizon_years)
        return result

    grid_years, grid_d = annual_grid(years, d)
    if len(grid_d) < 3:
        fill_flat(result, last_year, last_dist, horizon_years)
        return result

    try:
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA
        z = float(_norm.ppf(1 - (1 - ci) / 2))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = _ARIMA(grid_d, order=(1, 1, 1), trend="t").fit()
        pred = fit.get_forecast(steps=horizon_years)
        fc = pred.predicted_mean
        se = pred.se_mean
        fut_years = [last_year + i for i in range(1, horizon_years + 1)]
        result.forecast_years = fut_years
        result.forecast_distances = fc.tolist()
        result.forecast_lower = (fc - z * se).tolist()
        result.forecast_upper = (fc + z * se).tolist()
    except Exception:
        fill_flat(result, last_year, last_dist, horizon_years)
    return result
