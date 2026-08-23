"""Unit tests for the holdout scorecard validation (train 1..N-1, test N)."""
from datetime import date
import pytest

from shift.models import TransectSeries
from shift.validation.scorecard import build_scorecard


def _make_series(rates_per_year: float = -10.0, n: int = 6) -> TransectSeries:
    start_year = 1995
    years = [start_year + i * 5 for i in range(n)]
    d0 = 500.0
    dates = [date(y, 1, 1) for y in years]
    distances = [d0 + rates_per_year * (y - start_year) for y in years]
    uncertainties = [5.0] * n
    return TransectSeries(transect_id=1, dates=dates, distances=distances, uncertainties=uncertainties)


def test_holdout_scorecard_perfect_linear():
    """On a perfectly linear series, LRR holdout prediction should have ~0 error."""
    series_list = [_make_series(-10.0, 6) for _ in range(5)]
    sc = build_scorecard(series_list)
    assert sc["n_participating"] == 5
    assert sc["recommended"] is not None
    assert len(sc["rows"]) > 0

    lrr_row = next(r for r in sc["rows"] if r["method"] == "LRR")
    assert lrr_row["holdout_rmse"] == pytest.approx(0.0, abs=0.5)
    assert lrr_row["holdout_mae"] == pytest.approx(0.0, abs=0.5)


def test_holdout_scorecard_short_series_rejected():
    """Transects with fewer than 3 surveys cannot be holdout scored."""
    series_list = [_make_series(-10.0, 2)]
    sc = build_scorecard(series_list)
    assert sc["n_participating"] == 0
    assert sc["recommended"] is None
