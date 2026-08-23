"""Robust regression methods for shoreline change analysis.

Protects against satellite positional outliers, tidal spike noise, and georeferencing artifacts:
1. Theil-Sen Estimator: Non-parametric median-of-slopes estimator with 29.3% breakdown point.
2. RANSAC (Random Sample Consensus): Iterative inlier/outlier partitioning regression.
"""
from __future__ import annotations

import math
import warnings
import numpy as np
from scipy import stats as st
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.linear_model import LinearRegression, RANSACRegressor, TheilSenRegressor


from shift.models import RateResult, TransectSeries
from shift.stats.base import BaseMethod


class TheilSenMethod(BaseMethod):
    """
    Theil-Sen Robust Estimator.
    
    Computes the median of all pairwise slopes between shoreline observations.
    Highly resistant to arbitrary outliers (up to ~29.3% contamination).
    """

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state

    def fit(self, series: TransectSeries) -> RateResult:
        n = len(series)
        if n < 2:
            return RateResult(transect_id=series.transect_id, method="theilsen")

        years = np.array(series.years())
        d = np.array(series.distances)

        if n < 4:
            # Fallback to scipy theilslopes for very short series
            res = st.theilslopes(d, years, alpha=0.90)
            slope = float(res.slope)
            intercept = float(res.intercept)

        else:
            ts = TheilSenRegressor(random_state=self.random_state)
            ts.fit(years.reshape(-1, 1), d)
            slope = float(ts.coef_[0])
            intercept = float(ts.intercept_)

        y_pred = slope * years + intercept
        sse = float(np.sum((d - y_pred) ** 2))
        sst = float(np.sum((d - np.mean(d)) ** 2)) or 1e-10
        r2 = float(max(0.0, min(1.0, 1.0 - (sse / sst))))

        return RateResult(
            transect_id=series.transect_id,
            method="theilsen",
            theilsen=slope,
            theilsen_r2=r2,
            overall_rate=slope,
        )


class RansacMethod(BaseMethod):
    """
    RANSAC (Random Sample Consensus) Robust Regressor.
    
    Identifies inlier consensus subsets and separates out positional outliers
    caused by cloud shadows, tide spikes, or manual digitization error.
    """

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state

    def fit(self, series: TransectSeries) -> RateResult:
        n = len(series)
        if n < 2:
            return RateResult(transect_id=series.transect_id, method="ransac")

        years = np.array(series.years())
        d = np.array(series.distances)

        if n < 4:
            # Fallback to standard OLS if too few points for RANSAC partitioning
            res = st.linregress(years, d)
            return RateResult(
                transect_id=series.transect_id,
                method="ransac",
                ransac=float(res.slope),
                ransac_r2=float(res.rvalue ** 2),
                ransac_outliers=0,
                overall_rate=float(res.slope),
            )

        min_samples = max(2, min(3, n - 1))
        # Residual threshold: 2.5x median survey uncertainty (or 20 m when no
        # uncertainty data), floored at 10 m so it never collapses to ~0.
        thresh = float(np.median(series.uncertainties) * 2.5) if series.uncertainties else 20.0
        thresh = max(10.0, thresh)

        ransac = RANSACRegressor(
            estimator=LinearRegression(),
            min_samples=min_samples,
            residual_threshold=thresh,
            random_state=self.random_state,
            max_trials=100,
        )


        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UndefinedMetricWarning)
            warnings.simplefilter("ignore", category=RuntimeWarning)
            try:
                ransac.fit(years.reshape(-1, 1), d)
                slope = float(ransac.estimator_.coef_[0])
                intercept = float(ransac.estimator_.intercept_)
                n_outliers = int(np.sum(~ransac.inlier_mask_)) if ransac.inlier_mask_ is not None else 0
            except Exception:
                # Fallback if RANSAC fails on singular geometries
                res = st.linregress(years, d)
                slope = float(res.slope)
                intercept = float(res.intercept)
                n_outliers = 0

        # Coefficient of determination of the fitted RANSAC line over all points.
        y_pred = slope * years + intercept
        sse = float(np.sum((d - y_pred) ** 2))
        sst = float(np.sum((d - np.mean(d)) ** 2)) or 1e-10
        r2 = float(max(0.0, min(1.0, 1.0 - (sse / sst))))

        return RateResult(
            transect_id=series.transect_id,
            method="ransac",
            ransac=slope,
            ransac_r2=r2,
            ransac_outliers=n_outliers,
            overall_rate=slope,
        )
