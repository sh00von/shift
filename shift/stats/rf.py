"""
Random Forest benchmark — ML comparison method.

Trains on (year → distance) per transect using leave-one-out
endpoint hold-out: fit on all dates except the last, predict last.
"""
from __future__ import annotations

import warnings
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import UndefinedMetricWarning


from shift.models import RateResult, TransectSeries
from shift.stats.base import BaseMethod


class RandomForestMethod(BaseMethod):
    """
    Parameters
    ----------
    n_estimators    Number of trees
    holdout         If True, hold out the last date as prediction target
    """

    def __init__(self, n_estimators: int = 200, holdout: bool = True) -> None:
        self.n_estimators = n_estimators
        self.holdout = holdout

    def fit(self, series: TransectSeries) -> RateResult:
        years = np.array(series.years()).reshape(-1, 1)
        d = np.array(series.distances)

        if self.holdout and len(series) >= 3:
            X_train, y_train = years[:-1], d[:-1]
            X_test, y_test = years[-1:], d[-1:]
        else:
            X_train, y_train = years, d
            X_test, y_test = years, d

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UndefinedMetricWarning)
            warnings.simplefilter("ignore", category=RuntimeWarning)
            rf = RandomForestRegressor(
                n_estimators=self.n_estimators,
                random_state=42,
            )
            rf.fit(X_train, y_train)
            pred = rf.predict(X_test)
            rmse = float(np.sqrt(np.mean((pred - y_test) ** 2)))


        rate = float(np.polyfit(years.ravel(), d, 1)[0]) if len(d) >= 2 else 0.0

        return RateResult(
            transect_id=series.transect_id,
            method="rf",
            rf_prediction=float(pred[0]),
            rf_rmse=rmse,
            overall_rate=rate,
        )
