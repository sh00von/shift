"""Logarithmic trend forecast: distance ~ a + b·log(t − t₀ + 1)."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import fill_flat


def logarithmic_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast via logarithmic trend.

    Models beaches that erode rapidly then reach a new equilibrium — a
    physically motivated pattern in post-storm recovery and chronic erosion
    with negative feedback. Falls back to flat extrapolation if the log fit
    is degenerate.
    """
    from scipy.stats import t as t_dist
    from scipy.optimize import curve_fit

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])

    result = RateResult(transect_id=series.transect_id, method="logarithmic")
    fut_years = [last_year + i for i in range(1, horizon_years + 1)]

    if len(years) < 3:
        fill_flat(result, last_year, float(d[-1]), horizon_years)
        return result

    try:
        t0 = float(years[0])
        x = years - t0 + 1.0  # shift so log argument is always ≥ 1

        def log_model(x_, a, b):
            return a + b * np.log(x_)

        popt, pcov = curve_fit(log_model, x, d, maxfev=2000)
        a, b = float(popt[0]), float(popt[1])

        fitted = log_model(x, a, b)
        n, p = len(years), 2
        dof = max(n - p, 1)
        sigma2 = max(float(np.sum((d - fitted) ** 2)) / dof, 1e-6)
        t_crit = float(t_dist.ppf(1 - (1 - ci) / 2, df=dof))

        x_fut = np.array(fut_years) - t0 + 1.0
        fc = log_model(x_fut, a, b).tolist()

        J = np.column_stack([np.ones_like(x_fut), np.log(x_fut)])
        pred_vars = np.array([float(j @ pcov @ j) for j in J])
        margin = t_crit * np.sqrt(np.maximum(pred_vars, 0) + sigma2)

        result.forecast_years = fut_years
        result.forecast_distances = fc
        result.forecast_lower = (np.array(fc) - margin).tolist()
        result.forecast_upper = (np.array(fc) + margin).tolist()
    except Exception:
        fill_flat(result, last_year, float(d[-1]), horizon_years)
    return result
