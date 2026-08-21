"""Classic DSAS metrics: SCE, NSM, EPR, LRR, WLR."""
from __future__ import annotations

import numpy as np

from shift.models import RateResult, TransectSeries
from shift.stats.base import BaseMethod


class DSASMethod(BaseMethod):
    """Replicates USGS DSAS metrics: EPR, LRR, WLR, NSM, SCE per transect."""

    def fit(self, series: TransectSeries) -> RateResult:
        if len(series) < 2:
            raise ValueError(f"Transect {series.transect_id}: need ≥2 shorelines.")

        years = np.array(series.years())
        d = np.array(series.distances)
        u = np.array(series.uncertainties)

        sce = float(np.max(d) - np.min(d))
        nsm = float(d[-1] - d[0])
        epr = nsm / (years[-1] - years[0])

        # LRR — ordinary least squares
        lrr, lrr_r2 = _ols(years, d)

        # WLR — weighted by 1/uncertainty²
        weights = 1.0 / np.maximum(u, 0.01) ** 2
        wlr, wlr_r2 = _wls(years, d, weights)

        return RateResult(
            transect_id=series.transect_id,
            method="dsas",
            sce=sce,
            nsm=nsm,
            epr=epr,
            lrr=lrr,
            lrr_r2=lrr_r2,
            wlr=wlr,
            wlr_r2=wlr_r2,
        )


# Backward compatibility alias
ClassicMethod = DSASMethod


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    coeffs = np.polyfit(x, y, 1)
    y_hat = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(coeffs[0]), float(r2)


def _wls(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    W = np.diag(w)
    X = np.column_stack([x, np.ones_like(x)])
    try:
        coeffs = np.linalg.lstsq(X.T @ W @ X, X.T @ W @ y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return _ols(x, y)
    y_hat = X @ coeffs
    ss_res = np.sum(w * (y - y_hat) ** 2)
    ss_tot = np.sum(w * (y - np.average(y, weights=w)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(coeffs[0]), float(r2)
