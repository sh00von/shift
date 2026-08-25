"""Hindcast evaluation of forecast models.

For each selected forecast model, withholds the most recent survey (N),
trains on surveys 1..N-1, forecasts to survey N's year, and measures error
against the actual position. This is forecast accuracy validation — not rate
analysis validation.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np

from shift.models import TransectSeries

ProgressCB = Callable[[str, float], None]

FORECAST_MODELS = [
    "Kalman Filter (DSAS)",
    "EKF Rate",
    "ARIMA",
    "Holt Exponential Smoothing",
    "Linear Regression (LRR)",
    "Classic Endpoint Rate (EPR)",
]


def _truncated(series: TransectSeries) -> TransectSeries:
    """Return series with last survey withheld."""
    return TransectSeries(
        transect_id=series.transect_id,
        dates=series.dates[:-1],
        distances=series.distances[:-1],
        uncertainties=series.uncertainties[:-1],
    )


def _predict_one(model: str, series: TransectSeries, target_year: float) -> float | None:
    """Run model on series, forecast to target_year, return predicted position."""
    from shift.stats import DSASMethod, EKFMethod, arima_forecast, holt_forecast
    from shift.forecast.extrapolate import forecast as lin_forecast, kalman_forecast

    years = np.array(series.years(), dtype=float)
    d = np.array(series.distances, dtype=float)
    horizon = int(math.ceil(target_year - years[-1]))
    if horizon < 1:
        horizon = 1

    try:
        if model == "Kalman Filter (DSAS)":
            res = DSASMethod().fit(series)
            res = kalman_forecast(res, series, horizon_years=horizon)
        elif model == "EKF Rate":
            res = EKFMethod().fit(series)
            res = lin_forecast(res, series, horizon_years=horizon)
        elif model == "ARIMA":
            res = arima_forecast(series, horizon_years=horizon)
        elif model == "Holt Exponential Smoothing":
            res = holt_forecast(series, horizon_years=horizon)
        elif model == "Linear Regression (LRR)":
            res = DSASMethod().fit(series)
            res = lin_forecast(res, series, horizon_years=horizon)
        elif model == "Classic Endpoint Rate (EPR)":
            res = DSASMethod().fit(series)
            if res.epr is not None:
                res.lrr = res.epr  # use EPR as driving rate
            res = lin_forecast(res, series, horizon_years=horizon)
        else:
            return None

        if not res.forecast_years:
            return None
        # Interpolate forecast to exact target year
        fy = np.array(res.forecast_years)
        fd = np.array(res.forecast_distances)
        return float(np.interp(target_year, fy, fd))
    except Exception:
        return None


def evaluate_forecasts(
    series_list: list[TransectSeries],
    models: list[str],
    progress: ProgressCB | None = None,
) -> dict[str, dict]:
    """
    Hindcast evaluation across all transects for each selected forecast model.

    Returns dict keyed by model name:
      {rmse, mae, n, per_transect: [{transect_id, actual, predicted, error}]}
    """
    total = len(series_list)
    results: dict[str, dict] = {
        m: {"sq_errors": [], "abs_errors": [], "per_transect": []} for m in models
    }

    for i, series in enumerate(series_list):
        if progress and (i % 10 == 0 or i == total - 1):
            progress(f"Evaluating forecast models {i + 1}/{total}…",
                     0.1 + 0.85 * (i + 1) / max(total, 1))

        if len(series) < 3:
            continue

        truncated = _truncated(series)
        actual = float(series.distances[-1])
        target_year = float(series.years()[-1])

        for model in models:
            pred = _predict_one(model, truncated, target_year)
            if pred is None or math.isnan(pred):
                continue
            err = actual - pred
            results[model]["sq_errors"].append(err ** 2)
            results[model]["abs_errors"].append(abs(err))
            results[model]["per_transect"].append({
                "transect_id": int(series.transect_id),
                "actual": round(actual, 2),
                "predicted": round(pred, 2),
                "error": round(err, 2),
            })

    out = {}
    for model in models:
        sq = results[model]["sq_errors"]
        ab = results[model]["abs_errors"]
        out[model] = {
            "rmse": round(float(np.sqrt(np.mean(sq))), 2) if sq else None,
            "mae": round(float(np.mean(ab)), 2) if ab else None,
            "n": len(sq),
            "per_transect": results[model]["per_transect"],
        }
    return out
