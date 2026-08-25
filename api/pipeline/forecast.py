"""Forecast pipeline: run all selected models and evaluate with hindcast."""
from __future__ import annotations

from typing import Callable

from shift.forecast import (
    forecast as run_forecast,
    kalman_forecast as run_kalman_forecast,
    arima_forecast,
    holt_forecast,
    polynomial_forecast,
    logarithmic_forecast,
)
from shift.validation import evaluate_forecasts

from api.session import Session

ProgressCB = Callable[[str, float], None]


def generate_forecast(state: Session, progress: ProgressCB):
    """Run all selected forecast models and evaluate each with a hindcast."""
    if not state.results or not state.series_list:
        return {}

    models = state.forecast_models or ["Kalman Filter (DSAS)"]
    n_total = len(state.series_list)
    r = state.results
    all_forecasts: dict = {}

    for idx, model in enumerate(models):
        base_prog = 0.05 + 0.55 * idx / len(models)
        progress(f"Forecasting {state.forecast_horizon} yr — {model}…", base_prog)
        fc_list = []

        if "Kalman" in model:
            source = r.get("classic") or r.get("ekf") or []
            for s, res in zip(state.series_list, source):
                fc_list.append(
                    run_kalman_forecast(res, s, horizon_years=state.forecast_horizon, ci=state.forecast_ci)
                    if res is not None else None
                )
        elif "ARIMA" in model:
            for s in state.series_list:
                fc_list.append(arima_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Holt" in model:
            for s in state.series_list:
                fc_list.append(holt_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Polynomial" in model:
            for s in state.series_list:
                fc_list.append(polynomial_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Logarithmic" in model:
            for s in state.series_list:
                fc_list.append(logarithmic_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "EKF" in model:
            source = r.get("ekf") or r.get("classic") or []
            for s, res in zip(state.series_list, source):
                fc_list.append(
                    run_forecast(res, s, horizon_years=state.forecast_horizon, ci=state.forecast_ci)
                    if res is not None else None
                )
        else:
            fc_list = [None] * len(state.series_list)

        all_forecasts[model] = fc_list

    state.results["forecast"] = all_forecasts.get(models[0], [])
    state.results["forecasts"] = all_forecasts
    state.forecast_model = models[0]

    progress("Running hindcast evaluation across forecast models…", 0.65)
    eval_result = evaluate_forecasts(
        state.series_list, models,
        progress=lambda m, p: progress(m, 0.65 + 0.30 * p),
    )
    state.forecast_eval = eval_result

    progress(f"Forecast complete — {len(models)} model(s), {n_total} transects.", 1.0)
    return all_forecasts
