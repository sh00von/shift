"""DSAS-parity tests for DSASMethod."""
from datetime import date
import numpy as np
import pytest

from shift.models import TransectSeries
from shift.stats.classic import DSASMethod, ClassicMethod


def _make_series(rates_per_year: float = -37.58, n: int = 7) -> TransectSeries:
    """Synthetic series matching ~your Bangladesh DSAS run."""
    start_year = 1995
    years = [start_year + i * 5 for i in range(n)]
    d0 = 1000.0
    dates = [date(y, 1, 1) for y in years]
    distances = [d0 + rates_per_year * (y - start_year) for y in years]
    uncertainties = [10.0] * n
    return TransectSeries(transect_id=0, dates=dates,
                          distances=distances, uncertainties=uncertainties)


def test_epr_matches_known_rate():
    series = _make_series(rates_per_year=-37.58)
    result = DSASMethod().fit(series)
    assert result.epr == pytest.approx(-37.58, abs=0.1)


def test_lrr_matches_epr_on_linear_series():
    """On a perfectly linear series, LRR == EPR."""
    series = _make_series(rates_per_year=-50.0)
    result = DSASMethod().fit(series)
    assert result.lrr == pytest.approx(result.epr, abs=0.5)


def test_sce_is_positive():
    series = _make_series()
    result = DSASMethod().fit(series)
    assert result.sce > 0


def test_nsm_negative_for_erosional():
    series = _make_series(rates_per_year=-37.58)
    result = DSASMethod().fit(series)
    assert result.nsm < 0


def test_classic_alias():
    series = _make_series(rates_per_year=-37.58)
    result = ClassicMethod().fit(series)
    assert result.epr == pytest.approx(-37.58, abs=0.1)
