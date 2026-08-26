"""Linear extrapolation forecast using the fitted rate (EKF > LRR > EPR fallback)."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import strip_outliers


def forecast(
    result: RateResult,
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Extrapolate the most recent era's rate forward `horizon_years`.

    Uses EKF, LRR, or EPR rate. Uncertainty bands grow linearly with time
    using the propagated slope standard error from the data residuals.
    """
    series = strip_outliers(series)
    years = np.array(series.years())
    d = np.array(series.distances)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    if result.ekf is not None:
        rate = result.ekf
    elif result.lrr is not None:
        rate = result.lrr
    elif result.epr is not None:
        rate = result.epr
    else:
        rate = float(np.polyfit(years, d, 1)[0]) if len(years) >= 2 else 0.0

    se = _slope_stderr(years, d, rate)
    rate_uncertainty = se if se is not None else abs(rate) * 0.15

    horizon_years = int(horizon_years)
    future_years = [last_year + i for i in range(1, horizon_years + 1)]
    future_dists = [last_dist + rate * (y - last_year) for y in future_years]

    z = _z_from_ci(ci)
    future_lower = [d_ - z * rate_uncertainty * (y - last_year)
                    for d_, y in zip(future_dists, future_years)]
    future_upper = [d_ + z * rate_uncertainty * (y - last_year)
                    for d_, y in zip(future_dists, future_years)]

    result.forecast_years = future_years
    result.forecast_distances = future_dists
    result.forecast_lower = future_lower
    result.forecast_upper = future_upper
    return result


def _slope_stderr(years: np.ndarray, d: np.ndarray, rate: float) -> float | None:
    n = len(years)
    if n < 3:
        return None
    ss_x = float(np.sum((years - years.mean()) ** 2))
    if ss_x <= 0:
        return None
    intercept = float(np.mean(d) - rate * np.mean(years))
    resid = d - (rate * years + intercept)
    resid_var = float(np.sum(resid ** 2) / (n - 2))
    return float(np.sqrt(resid_var / ss_x))


def _z_from_ci(ci: float) -> float:
    from scipy.stats import norm
    return float(norm.ppf(1 - (1 - ci) / 2))
