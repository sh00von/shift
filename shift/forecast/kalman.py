"""DSAS-style Kalman Filter forecast (Long & Plant, 2012)."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.forecast._utils import strip_outliers


def kalman_forecast(
    result: RateResult,
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """DSAS-style Kalman-filter forecast.

    Models shoreline evolution with a linear state-space filter whose state is
    x = [position (m), rate (m/yr)]. Each survey is assimilated as a noisy
    measurement of position (measurement variance = positional uncertainty²),
    letting the filter recursively refine both position and rate. The forecast
    phase runs prediction-only steps so the band grows from the propagated
    state covariance — the same recursive estimator USGS DSAS uses.
    """
    from scipy.stats import norm
    series = strip_outliers(series)
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

    slope, intercept = np.polyfit(years, d, 1)
    resid = d - (slope * years + intercept)
    dof = max(len(years) - 2, 1)
    resid_var = float(np.sum(resid ** 2) / dof)
    ss_x = float(np.sum((years - years.mean()) ** 2)) or 1.0
    slope_var = resid_var / ss_x

    x = np.array([d[0], slope], dtype=float)
    P = np.array([[max(unc[0], 1.0) ** 2, 0.0],
                  [0.0, max(slope_var, (abs(slope) * 0.5 + 0.05) ** 2)]])
    H = np.array([[1.0, 0.0]])
    q_rate = max(slope_var * 0.1, (abs(slope) * 0.02 + 0.01) ** 2)

    def _predict(x_, P_, dt):
        F = np.array([[1.0, dt], [0.0, 1.0]])
        Q = np.array([[q_rate * dt ** 3 / 3.0, q_rate * dt ** 2 / 2.0],
                      [q_rate * dt ** 2 / 2.0, q_rate * dt]])
        return F @ x_, F @ P_ @ F.T + Q

    for k in range(1, len(years)):
        dt = float(years[k] - years[k - 1]) or 1e-6
        x, P = _predict(x, P, dt)
        R = np.array([[max(unc[k], 1.0) ** 2]])
        y_innov = d[k] - (H @ x)[0]
        S = (H @ P @ H.T + R)[0, 0]
        K = (P @ H.T / S).reshape(2)
        x = x + K * y_innov
        P = (np.eye(2) - np.outer(K, H)) @ P

    z = float(norm.ppf(1 - (1 - ci) / 2))
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
