"""Polynomial (quadratic) regression forecast."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import fill_flat, strip_outliers


def polynomial_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
    degree: int = 2,
) -> RateResult:
    """Forecast via polynomial (quadratic by default) regression on decimal years.

    Fits distance ~ β₀ + β₁·t + β₂·t² via OLS, then extrapolates forward.
    CI derived from the prediction variance of the polynomial fit. Useful when
    erosion/accretion is accelerating or decelerating (non-linear trend).
    """
    from scipy.stats import t as t_dist

    series = strip_outliers(series)
    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])

    result = RateResult(transect_id=series.transect_id, method="polynomial")
    fut_years = [last_year + i for i in range(1, horizon_years + 1)]

    if len(years) < degree + 1:
        fill_flat(result, last_year, float(d[-1]), horizon_years)
        return result

    try:
        t0 = years.mean()
        t_cent = years - t0
        V = np.vander(t_cent, N=degree + 1, increasing=True)
        coeffs, residuals, rank, _ = np.linalg.lstsq(V, d, rcond=None)

        n, p = len(years), degree + 1
        dof = max(n - p, 1)
        sigma2 = (float(residuals[0]) / dof
                  if residuals.size
                  else float(np.sum((d - V @ coeffs) ** 2)) / dof)
        sigma2 = max(sigma2, 1e-6)

        VtV_inv = np.linalg.pinv(V.T @ V)
        t_crit = float(t_dist.ppf(1 - (1 - ci) / 2, df=dof))

        fut_cent = np.array(fut_years) - t0
        V_fut = np.vander(fut_cent, N=degree + 1, increasing=True)
        fc = (V_fut @ coeffs).tolist()
        pred_vars = np.array([float(v @ VtV_inv @ v) * sigma2 for v in V_fut])
        margin = t_crit * np.sqrt(pred_vars + sigma2)

        result.forecast_years = fut_years
        result.forecast_distances = fc
        result.forecast_lower = (np.array(fc) - margin).tolist()
        result.forecast_upper = (np.array(fc) + margin).tolist()
    except Exception:
        fill_flat(result, last_year, float(d[-1]), horizon_years)
    return result
