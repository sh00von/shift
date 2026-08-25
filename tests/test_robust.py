"""Tests for robust-like behaviour using DSASMethod and EKF (TheilSen/RANSAC removed)."""
from datetime import date
import pytest

from shift.models import TransectSeries
from shift.stats.classic import DSASMethod
from shift.stats.ekf import EKFMethod
from shift.forecast import forecast


def _make_series(years: list[int], distances: list[float], tid: int = 1) -> TransectSeries:
    dates = [date(y, 6, 15) for y in years]
    return TransectSeries(
        transect_id=tid,
        dates=dates,
        distances=distances,
        uncertainties=[10.0] * len(years),
    )


def test_classic_linear_recovery():
    """DSASMethod recovers true linear slope on clean data."""
    years = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
    distances = [1000 - 5 * (y - 1990) for y in years]
    series = _make_series(years, distances)
    res = DSASMethod().fit(series)
    assert res.lrr is not None
    assert pytest.approx(res.lrr, abs=0.1) == -5.0


def test_ekf_method():
    """EKFMethod returns a valid rate on clean data."""
    years = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
    distances = [1000 - 3 * (y - 1990) for y in years]
    series = _make_series(years, distances)
    res = EKFMethod().fit(series)
    assert res.ekf is not None


def test_forecast_from_classic():
    """Forecast extrapolation works from DSASMethod result."""
    years = [1990, 1995, 2000, 2005, 2010]
    distances = [500 - 4 * (y - 1990) for y in years]
    series = _make_series(years, distances)
    res = DSASMethod().fit(series)
    fc = forecast(res, series, horizon_years=5, ci=0.90)
    assert len(fc.forecast_years) == 5
    assert pytest.approx(fc.forecast_years[-1], abs=0.5) == 2015.0
    assert pytest.approx(fc.forecast_distances[-1], abs=2.0) == 400.0
