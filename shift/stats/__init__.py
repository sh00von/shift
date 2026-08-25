"""Analysis methods — one module per algorithm."""
from shift.stats.classic import DSASMethod, ClassicMethod
from shift.stats.ekf import EKFMethod
from shift.stats.spatial import morans_i, smooth_rates
from shift.stats.cbc import classify, classify_all, LABELS, LABEL_COLORS
from shift.stats.aln2d import ALN2DEngine

# Forecast re-exports kept here for backwards compatibility with pipeline imports
from shift.forecast.arima import arima_forecast
from shift.forecast.holt import holt_forecast
from shift.forecast.polynomial import polynomial_forecast
from shift.forecast.logarithmic import logarithmic_forecast

__all__ = [
    "DSASMethod",
    "ClassicMethod",
    "EKFMethod",
    "morans_i",
    "smooth_rates",
    "classify",
    "classify_all",
    "LABELS",
    "LABEL_COLORS",
    "ALN2DEngine",
    "arima_forecast",
    "holt_forecast",
    "polynomial_forecast",
    "logarithmic_forecast",
]
