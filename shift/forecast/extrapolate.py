"""Extrapolate a fitted RateResult N years forward with uncertainty bands."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries


def forecast(
    result: RateResult,
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """
    Extrapolate the most recent era's rate forward `horizon_years`.

    Uses the final segment rate from breakpoint/Bayesian results,
    or LRR/EPR from classic results. Uncertainty bands grow linearly
    with time using the CI from the last segment.

    Modifies `result` in-place (appends forecast fields) and returns it.
    """
    years = np.array(series.years())
    d = np.array(series.distances)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    if result.breakpoints:
        bp = result.breakpoints[-1]
        rate = bp.rate_after
        ci_low, ci_high = bp.ci_after
        rate_uncertainty = (ci_high - ci_low) / 2
    elif result.theilsen is not None:
        rate = result.theilsen
        rate_uncertainty = abs(rate) * 0.12
    elif result.ransac is not None:
        rate = result.ransac
        rate_uncertainty = abs(rate) * 0.12
    elif result.lrr is not None:
        rate = result.lrr
        rate_uncertainty = abs(rate) * 0.15  # 15% fallback uncertainty
    elif result.epr is not None:
        rate = result.epr
        rate_uncertainty = abs(rate) * 0.15
    elif result.overall_rate is not None:
        rate = result.overall_rate
        rate_uncertainty = (result.rf_rmse if getattr(result, "rf_rmse", None) else abs(rate) * 0.15)
    elif getattr(result, "rf_prediction", None) is not None:
        rate = float(np.polyfit(years, d, 1)[0]) if len(years) >= 2 else 0.0
        rate_uncertainty = (result.rf_rmse if getattr(result, "rf_rmse", None) else abs(rate) * 0.15)
    else:
        rate = float(np.polyfit(years, d, 1)[0]) if len(years) >= 2 else 0.0
        rate_uncertainty = abs(rate) * 0.15


    horizon_years = int(horizon_years)
    future_years = [last_year + i for i in range(1, horizon_years + 1)]
    future_dists = [last_dist + rate * (y - last_year) for y in future_years]



    # Uncertainty bands grow linearly with time
    z = _z_from_ci(ci)
    future_lower = [d - z * rate_uncertainty * (y - last_year)
                    for d, y in zip(future_dists, future_years)]
    future_upper = [d + z * rate_uncertainty * (y - last_year)
                    for d, y in zip(future_dists, future_years)]

    result.forecast_years = future_years
    result.forecast_distances = future_dists
    result.forecast_lower = future_lower
    result.forecast_upper = future_upper
    return result


def _z_from_ci(ci: float) -> float:
    from scipy.stats import norm
    return float(norm.ppf(1 - (1 - ci) / 2))
