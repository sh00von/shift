"""Extended Kalman Filter rate estimator for shoreline transects."""
from __future__ import annotations

import numpy as np
from scipy import stats as st

from shift.models import RateResult, TransectSeries
from shift.stats.base import BaseMethod


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
