"""Synthetic ground-truth test for BreakpointMethod."""
from datetime import date
import pytest

from shift.models import TransectSeries
from shift.stats.breakpoint import BreakpointMethod


def _make_break_series(
    break_year: int = 2010,
    rate_before: float = -10.0,
    rate_after: float = -60.0,
) -> TransectSeries:
    """
    Synthetic series with a KNOWN break at break_year.
    Rate switches from rate_before to rate_after at that year.
    Dates: 1995, 2000, 2005, 2010, 2015, 2020, 2025.
    """
    all_years = [1995, 2000, 2005, 2010, 2015, 2020, 2025]
    dates = [date(y, 1, 1) for y in all_years]
    d = 1000.0
    distances = []
    prev_year = all_years[0]
    distances.append(d)
    for y in all_years[1:]:
        rate = rate_before if y <= break_year else rate_after
        d += rate * (y - prev_year)
        distances.append(d)
        prev_year = y
    return TransectSeries(
        transect_id=99,
        dates=dates,
        distances=distances,
        uncertainties=[10.0] * len(all_years),
    )


def test_breakpoint_detects_planted_break():
    series = _make_break_series(break_year=2010, rate_before=-10.0, rate_after=-60.0)
    result = BreakpointMethod(penalty=50.0).fit(series)
    assert len(result.breakpoints) >= 1, "Expected at least one break to be detected"
    break_years = [bp.year for bp in result.breakpoints]
    # Planted break at 2010 — allow ±1 year tolerance
    assert any(abs(by - 2010) <= 1 for by in break_years), (
        f"Break not recovered near 2010, got: {break_years}"
    )


def test_breakpoint_rate_after_is_strongly_negative():
    series = _make_break_series(break_year=2010, rate_before=-10.0, rate_after=-60.0)
    result = BreakpointMethod(penalty=50.0).fit(series)
    assert result.overall_rate is not None
    assert result.overall_rate < -20.0, (
        f"Expected strongly negative post-break rate, got {result.overall_rate:.1f}"
    )


def test_no_break_on_linear_series():
    """A perfectly linear series should produce zero or one spurious break."""
    from datetime import date as d
    years = [1995, 2000, 2005, 2010, 2015, 2020, 2025]
    distances = [1000.0 - 30.0 * (y - 1995) for y in years]
    series = TransectSeries(
        transect_id=0,
        dates=[d(y, 1, 1) for y in years],
        distances=distances,
        uncertainties=[10.0] * len(years),
    )
    result = BreakpointMethod().fit(series)
    # A genuinely linear series should have at most one spurious break
    assert len(result.breakpoints) <= 1
