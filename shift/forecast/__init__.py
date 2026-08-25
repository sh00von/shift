"""Forecast engines — one module per algorithm."""
from shift.forecast.linear import forecast
from shift.forecast.kalman import kalman_forecast
from shift.forecast.arima import arima_forecast
from shift.forecast.holt import holt_forecast
from shift.forecast.polynomial import polynomial_forecast
from shift.forecast.logarithmic import logarithmic_forecast

__all__ = [
    "forecast",
    "kalman_forecast",
    "arima_forecast",
    "holt_forecast",
    "polynomial_forecast",
    "logarithmic_forecast",
]
