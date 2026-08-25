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

    Uses EKF, LRR, or EPR rate. Uncertainty bands grow linearly
    with time using the CI from the last segment.

    Modifies `result` in-place (appends forecast fields) and returns it.
    """
    years = np.array(series.years())
    d = np.array(series.distances)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    # Pick the driving rate, then propagate the standard error of the slope
    # from the data (residuals around a best-fit line with that slope).
    if result.ekf is not None:
        rate = result.ekf
    elif result.lrr is not None:
        rate = result.lrr
    elif result.epr is not None:
        rate = result.epr
    else:
        rate = float(np.polyfit(years, d, 1)[0]) if len(years) >= 2 else 0.0
    se = _slope_stderr(years, d, rate)
    # Fall back to a 15% heuristic only when there are too few points to
    # estimate a standard error (n < 3).
    rate_uncertainty = se if se is not None else abs(rate) * 0.15



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


def _slope_stderr(years: np.ndarray, d: np.ndarray, rate: float) -> float | None:
    """Standard error of the trend (m/yr) given a fixed slope `rate`.

    Uses the residuals around the best-fit line that has this slope (least-squares
    intercept), i.e. se = sqrt( (SSE/(n-2)) / Σ(x-x̄)² ). Returns None when there
    are too few points (n < 3) or x has no spread.
    """
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


def kalman_forecast(
    result: RateResult,
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """DSAS-style Kalman-filter forecast (Long & Plant, 2012).

    Models shoreline evolution with a linear state-space filter whose state is
    ``x = [position (m), rate (m/yr)]``. Each survey is assimilated as a noisy
    measurement of position (measurement variance = the shoreline's positional
    uncertainty²), letting the filter recursively refine both the position and
    the trend rate. The forecast phase then runs prediction-only steps, so the
    forecast band grows from the propagated state covariance — the same
    recursive estimator the USGS DSAS forecasting tool uses, in place of the
    plain linear extrapolation in :func:`forecast`.

    Modifies ``result`` in-place (appends forecast fields) and returns it.
    """
    years = np.asarray(series.years(), dtype=float)
    d = np.asarray(series.distances, dtype=float)
    unc = np.asarray(series.uncertainties, dtype=float)

    horizon_years = int(horizon_years)

    if len(years) < 2:
        last_year = float(years[-1]) if len(years) else 0.0
        last_dist = float(d[-1]) if len(d) else 0.0
        result.forecast_years = [last_year + i for i in range(1, horizon_years + 1)]
        result.forecast_distances = [last_dist] * horizon_years
        result.forecast_lower = list(result.forecast_distances)
        result.forecast_upper = list(result.forecast_distances)
        return result

    order = np.argsort(years)
    years, d, unc = years[order], d[order], unc[order]

    # ── Initialise state from an OLS fit (position intercept + trend rate) ──
    slope, intercept = np.polyfit(years, d, 1)
    resid = d - (slope * years + intercept)
    dof = max(len(years) - 2, 1)
    resid_var = float(np.sum(resid ** 2) / dof)
    x_span = float(years[-1] - years[0]) or 1.0
    ss_x = float(np.sum((years - years.mean()) ** 2)) or 1.0
    slope_var = resid_var / ss_x  # standard OLS slope variance

    # State x = [position, rate]; start at the first survey.
    x = np.array([d[0], slope], dtype=float)
    P = np.array([[max(unc[0], 1.0) ** 2, 0.0],
                  [0.0, max(slope_var, (abs(slope) * 0.5 + 0.05) ** 2)]])

    H = np.array([[1.0, 0.0]])
    # Process noise: lets the rate drift slowly between surveys (per year).
    q_rate = max(slope_var * 0.1, (abs(slope) * 0.02 + 0.01) ** 2)

    def _predict(x, P, dt):
        F = np.array([[1.0, dt], [0.0, 1.0]])
        Q = np.array([[q_rate * dt ** 3 / 3.0, q_rate * dt ** 2 / 2.0],
                      [q_rate * dt ** 2 / 2.0, q_rate * dt]])
        return F @ x, F @ P @ F.T + Q

    # ── Filter across the surveys (predict → update) ──
    for k in range(1, len(years)):
        dt = float(years[k] - years[k - 1]) or 1e-6
        x, P = _predict(x, P, dt)
        R = np.array([[max(unc[k], 1.0) ** 2]])
        y_innov = d[k] - (H @ x)[0]
        S = (H @ P @ H.T + R)[0, 0]
        K = (P @ H.T / S).reshape(2)
        x = x + K * y_innov
        P = (np.eye(2) - np.outer(K, H)) @ P

    # ── Forecast phase: prediction-only steps beyond the last survey ──
    z = _z_from_ci(ci)
    last_year = float(years[-1])
    fut_years, fut_dist, fut_lo, fut_hi = [], [], [], []
    xf, Pf = x.copy(), P.copy()
    for i in range(1, horizon_years + 1):
        xf, Pf = _predict(xf, Pf, 1.0)
        pos_std = float(np.sqrt(max(Pf[0, 0], 0.0)))
        yr = last_year + i
        fut_years.append(yr)
        fut_dist.append(float(xf[0]))
        fut_lo.append(float(xf[0] - z * pos_std))
        fut_hi.append(float(xf[0] + z * pos_std))

    result.forecast_years = fut_years
    result.forecast_distances = fut_dist
    result.forecast_lower = fut_lo
    result.forecast_upper = fut_hi
    return result
