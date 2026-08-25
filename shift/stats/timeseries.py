"""Time-series methods for shoreline analysis.

EKFMethod — rate estimator (state-space velocity, used in analysis pipeline).
arima_forecast / holt_forecast — forecast engines (used in forecast pipeline only).
"""
from __future__ import annotations

import warnings
import numpy as np
from scipy import stats as st

from shift.models import RateResult, TransectSeries
from shift.stats.base import BaseMethod


def _annual_grid(years: np.ndarray, distances: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y0, y1 = int(np.floor(years[0])), int(np.ceil(years[-1]))
    grid = np.arange(y0, y1 + 1, dtype=float)
    interp = np.interp(grid, years, distances)
    return grid, interp



class EKFMethod(BaseMethod):
    """Extended Kalman Filter — state [position, velocity], noise tuned from data.

    R (measurement noise) is taken from per-survey uncertainty.
    Q (process noise) is estimated from the LRR residual variance.
    """

    def fit(self, series: TransectSeries) -> RateResult:
        n = len(series)
        if n < 2:
            return RateResult(transect_id=series.transect_id, method="ekf")

        years = np.array(series.years(), dtype=float)
        d = np.array(series.distances, dtype=float)
        w = np.maximum(np.array(series.uncertainties, dtype=float), 0.5)

        res = st.linregress(years, d)
        slope0 = float(res.slope)
        intercept0 = float(res.intercept)
        resid = d - (slope0 * years + intercept0)
        resid_var = float(np.sum(resid ** 2) / max(n - 2, 1))
        ss_x = float(np.sum((years - years.mean()) ** 2)) or 1.0

        state = np.array([intercept0 + slope0 * years[0], slope0], dtype=float)
        q_vel = max(resid_var / ss_x * 0.1, (abs(slope0) * 0.02 + 0.01) ** 2)
        P = np.array([[w[0] ** 2, 0.0], [0.0, q_vel * 10]])
        H = np.array([[1.0, 0.0]])

        fitted = [state[0]]
        vel_samples = [state[1]]
        vel_vars = [P[1, 1]]
        for k in range(1, n):
            dt = float(years[k] - years[k - 1]) or 1e-6
            F = np.array([[1.0, dt], [0.0, 1.0]])
            Q = np.array([[q_vel * dt ** 3 / 3, q_vel * dt ** 2 / 2],
                          [q_vel * dt ** 2 / 2, q_vel * dt]])
            state = F @ state
            P = F @ P @ F.T + Q
            R = np.array([[w[k] ** 2]])
            innov = d[k] - (H @ state)[0]
            S = (H @ P @ H.T + R)[0, 0]
            K = (P @ H.T / S).reshape(2)
            state = state + K * innov
            P = (np.eye(2) - np.outer(K, H)) @ P
            fitted.append(state[0])
            vel_samples.append(state[1])
            vel_vars.append(P[1, 1])

        fitted_arr = np.array(fitted)
        # Precision-weighted mean of the filter's velocity estimates (m/yr).
        # Using state[1] directly from the posterior at each step is the correct
        # EKF rate readout — not OLS on smoothed positions.
        vel_arr = np.array(vel_samples)
        prec = 1.0 / np.maximum(vel_vars, 1e-12)
        rate = float(np.sum(prec * vel_arr) / np.sum(prec))

        return RateResult(
            transect_id=series.transect_id,
            method="ekf",
            ekf=rate,
            fitted_years=years.tolist(),
            fitted_values=fitted_arr.tolist(),
        )


def arima_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast shoreline position using ARIMA (auto-order via pmdarima AIC stepwise).
    Produces forecast_years/distances/lower/upper on the returned RateResult."""
    from scipy.stats import norm as _norm

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    result = RateResult(transect_id=series.transect_id, method="arima")

    if len(years) < 3:
        _fill_flat(result, last_year, last_dist, horizon_years)
        return result

    grid_years, grid_d = _annual_grid(years, d)
    if len(grid_d) < 3:
        _fill_flat(result, last_year, last_dist, horizon_years)
        return result

    try:
        from pmdarima import auto_arima
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = auto_arima(
                grid_d, max_p=2, max_q=2, d=None,
                stepwise=True, information_criterion="aic",
                error_action="ignore", suppress_warnings=True,
            )
        fc, conf = model.predict(n_periods=horizon_years, return_conf_int=True, alpha=1 - ci)
        fut_years = [last_year + i for i in range(1, horizon_years + 1)]
        result.forecast_years = fut_years
        result.forecast_distances = fc.tolist()
        result.forecast_lower = conf[:, 0].tolist()
        result.forecast_upper = conf[:, 1].tolist()
    except Exception:
        _fill_flat(result, last_year, last_dist, horizon_years)
    return result


def holt_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast shoreline position using Holt's Linear Exponential Smoothing.
    Uncertainty bands grow with sqrt(steps) from in-sample residual std."""
    from scipy.stats import norm as _norm
    z = float(_norm.ppf(1 - (1 - ci) / 2))

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])
    last_dist = float(d[-1])

    result = RateResult(transect_id=series.transect_id, method="holt")

    if len(years) < 3:
        _fill_flat(result, last_year, last_dist, horizon_years)
        return result

    grid_years, grid_d = _annual_grid(years, d)
    if len(grid_d) < 3:
        _fill_flat(result, last_year, last_dist, horizon_years)
        return result

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(
                grid_d, trend="add", initialization_method="estimated",
            ).fit(optimized=True)
        fc = fit.forecast(horizon_years)
        resid_std = float(np.std(fit.resid)) if len(fit.resid) > 1 else abs(float(np.mean(grid_d)) * 0.05 + 1.0)
        fut_years = [last_year + i for i in range(1, horizon_years + 1)]
        result.forecast_years = fut_years
        result.forecast_distances = fc.tolist()
        result.forecast_lower = [v - z * resid_std * np.sqrt(i) for i, v in enumerate(fc, 1)]
        result.forecast_upper = [v + z * resid_std * np.sqrt(i) for i, v in enumerate(fc, 1)]
    except Exception:
        _fill_flat(result, last_year, last_dist, horizon_years)
    return result


def _fill_flat(result: RateResult, last_year: float, last_dist: float, horizon: int) -> None:
    result.forecast_years = [last_year + i for i in range(1, horizon + 1)]
    result.forecast_distances = [last_dist] * horizon
    result.forecast_lower = [last_dist] * horizon
    result.forecast_upper = [last_dist] * horizon
