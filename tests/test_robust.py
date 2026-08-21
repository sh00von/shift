"""Unit tests for Theil-Sen and RANSAC robust regression methods."""
from datetime import date
import pytest
import numpy as np

from shift.models import TransectSeries
from shift.stats.robust import TheilSenMethod, RansacMethod
from shift.stats.classic import DSASMethod
from shift.forecast import forecast


def _make_series(years: list[int], distances: list[float], tid: int = 1) -> TransectSeries:
    dates = [date(y, 6, 15) for y in years]
    return TransectSeries(
        transect_id=tid,
        dates=dates,
        distances=distances,
        uncertainties=[10.0] * len(years),
    )


def test_theilsen_clean_linear():
    """Verify Theil-Sen recovers true linear slope on clean data."""
    years = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
    # True slope: -5 m/yr, starting at 1000m
    distances = [1000 - 5 * (y - 1990) for y in years]
    series = _make_series(years, distances)

    ts = TheilSenMethod()
    res = ts.fit(series)

    assert res.theilsen is not None
    assert pytest.approx(res.theilsen, abs=0.1) == -5.0
    assert pytest.approx(res.theilsen_r2, abs=0.01) == 1.0


def test_theilsen_and_ransac_with_outlier():
    """Verify Theil-Sen and RANSAC ignore heavy satellite positional outliers."""
    years = [1990, 1995, 2000, 2005, 2010, 2015, 2020]
    # True slope: -10 m/yr
    distances = [1000 - 10 * (y - 1990) for y in years]
    
    # Inject heavy outlier at year 2005 (+150m tidal/cloud spike)
    distances[3] += 150.0

    series = _make_series(years, distances)

    # Classic OLS gets heavily distorted
    cl_res = DSASMethod().fit(series)
    assert cl_res.lrr != -10.0

    # Theil-Sen remains close to -10.0
    ts_res = TheilSenMethod().fit(series)
    assert ts_res.theilsen is not None
    assert pytest.approx(ts_res.theilsen, abs=2.0) == -10.0

    # RANSAC detects the outlier and computes robust slope
    rs_res = RansacMethod().fit(series)
    assert rs_res.ransac is not None
    assert pytest.approx(rs_res.ransac, abs=1.5) == -10.0
    assert rs_res.ransac_outliers >= 1


def test_robust_forecast():
    """Verify forecast extrapolation using Theil-Sen and RANSAC."""
    years = [1990, 1995, 2000, 2005, 2010]
    distances = [500 - 4 * (y - 1990) for y in years]
    series = _make_series(years, distances)

    ts_res = TheilSenMethod().fit(series)
    fc = forecast(ts_res, series, horizon_years=5, ci=0.90)

    assert len(fc.forecast_years) == 5
    assert pytest.approx(fc.forecast_years[-1], abs=0.5) == 2015.0

    # Expected last dist: 500 - 4*(2010-1990) - 4*5 = 500 - 80 - 20 = 400
    assert pytest.approx(fc.forecast_distances[-1], abs=1.0) == 400.0
