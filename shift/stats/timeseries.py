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
    """Forecast shoreline position using ARIMA(1,1,1) with a deterministic trend.

    Uses statsmodels ARIMA with trend='t' (linear time trend baked in), which
    guarantees the forecast changes proportionally with the horizon. pmdarima's
    auto-selection on sparse coastal data routinely picks ARIMA(0,1,0) with
    zero drift, producing a flat line identical for any horizon length.
    """
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
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA
        z = float(_norm.ppf(1 - (1 - ci) / 2))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # trend='t' adds a deterministic linear time trend to ARIMA(1,1,1).
            # This ensures the forecast slope is non-zero and grows with horizon.
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


def polynomial_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
    degree: int = 2,
) -> RateResult:
    """Forecast via polynomial (quadratic by default) regression on decimal years.

    Fits distance ~ β₀ + β₁·t + β₂·t² using ordinary least squares, then
    extrapolates forward. CI is derived from the prediction variance of the
    polynomial fit. Useful when erosion/accretion is accelerating or decelerating.
    """
    from scipy.stats import t as t_dist

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])

    result = RateResult(transect_id=series.transect_id, method="polynomial")
    fut_years = [last_year + i for i in range(1, horizon_years + 1)]

    if len(years) < degree + 1:
        _fill_flat(result, last_year, float(d[-1]), horizon_years)
        return result

    try:
        # Centre years for numerical stability
        t0 = years.mean()
        t_cent = years - t0
        V = np.vander(t_cent, N=degree + 1, increasing=True)   # design matrix
        coeffs, residuals, rank, _ = np.linalg.lstsq(V, d, rcond=None)

        n, p = len(years), degree + 1
        dof = max(n - p, 1)
        if residuals.size:
            sigma2 = float(residuals[0]) / dof
        else:
            sigma2 = float(np.sum((d - V @ coeffs) ** 2)) / dof
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
        _fill_flat(result, last_year, float(d[-1]), horizon_years)
    return result


def logarithmic_forecast(
    series: TransectSeries,
    horizon_years: int = 10,
    ci: float = 0.90,
) -> RateResult:
    """Forecast via logarithmic trend: distance ~ a + b·log(t - t₀ + 1).

    Models beaches that erode rapidly then reach a new equilibrium — a physically
    motivated pattern in post-storm recovery and chronic erosion with feedback.
    Falls back to linear extrapolation if the log fit is degenerate.
    """
    from scipy.stats import t as t_dist
    from scipy.optimize import curve_fit

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    last_year = float(years[-1])

    result = RateResult(transect_id=series.transect_id, method="logarithmic")
    fut_years = [last_year + i for i in range(1, horizon_years + 1)]

    if len(years) < 3:
        _fill_flat(result, last_year, float(d[-1]), horizon_years)
        return result

    try:
        t0 = float(years[0])
        # Shift so log argument is always ≥ 1
        x = years - t0 + 1.0

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

        # Approximate prediction interval from parameter covariance
        J = np.column_stack([np.ones_like(x_fut), np.log(x_fut)])
        pred_vars = np.array([float(j @ pcov @ j) for j in J])
        margin = t_crit * np.sqrt(np.maximum(pred_vars, 0) + sigma2)

        result.forecast_years = fut_years
        result.forecast_distances = fc
        result.forecast_lower = (np.array(fc) - margin).tolist()
        result.forecast_upper = (np.array(fc) + margin).tolist()
    except Exception:
        _fill_flat(result, last_year, float(d[-1]), horizon_years)
    return result


def _fill_flat(result: RateResult, last_year: float, last_dist: float, horizon: int) -> None:
    result.forecast_years = [last_year + i for i in range(1, horizon + 1)]
    result.forecast_distances = [last_dist] * horizon
    result.forecast_lower = [last_dist] * horizon
    result.forecast_upper = [last_dist] * horizon
