"""
Piecewise breakpoint regression — primary contribution.

For the short per-transect series typical in DSAS work (5–20 shorelines),
exhaustive search over candidate breakpoints with BIC model selection is
more reliable than PELT. For longer series (>20 points), PELT is used.

Output: break years + per-era rates with confidence intervals.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as st

from shift.models import Breakpoint, RateResult, TransectSeries
from shift.stats.base import BaseMethod
from shift.stats.classic import _ols


class BreakpointMethod(BaseMethod):
    """
    Parameters
    ----------
    min_segment     Minimum observations per segment (default 3). A 2-point
                    segment fits a line with zero residual, which biases BIC
                    toward spurious breaks, so >=3 is used.
    penalty         Override automatic BIC penalty (None = auto). NOTE: the app
                    always leaves this None; the explicit-penalty branch in
                    _exhaustive_search uses a raw-SSE scale that is not directly
                    comparable to the BIC baseline, so only pass it deliberately.
    max_breaks      Maximum number of breakpoints to consider
    """

    def __init__(
        self,
        min_segment: int = 3,
        penalty: float | None = None,
        max_breaks: int = 3,
    ) -> None:
        self.min_segment = min_segment
        self.penalty = penalty
        self.max_breaks = max_breaks

    def fit(self, series: TransectSeries) -> RateResult:
        n = len(series)
        if n < 4:
            from shift.stats.classic import DSASMethod
            r = DSASMethod().fit(series)
            r.method = "breakpoint"
            return r

        years = np.array(series.years())
        d = np.array(series.distances)

        if n <= 20:
            bp_indices = _exhaustive_search(years, d, self.min_segment,
                                            self.max_breaks, self.penalty)
        else:
            bp_indices = _pelt_on_rates(years, d, self.min_segment, self.penalty)

        segments = _split_segments(years, d, bp_indices)
        breakpoints = _fit_segments(segments)
        overall_rate = breakpoints[-1].rate_after if breakpoints else float(_ols(years, d)[0])

        return RateResult(
            transect_id=series.transect_id,
            method="breakpoint",
            breakpoints=breakpoints,
            overall_rate=overall_rate,
        )


# ---------------------------------------------------------------------------
# Exhaustive search (for short series ≤20 points)
# ---------------------------------------------------------------------------

def _ols_sse(x: np.ndarray, y: np.ndarray) -> float:
    """Sum of squared residuals from OLS fit."""
    if len(x) < 2:
        return 0.0
    slope, intercept, *_ = st.linregress(x, y)
    resid = y - (slope * x + intercept)
    return float(np.sum(resid ** 2))


def _total_sse(years: np.ndarray, d: np.ndarray, cuts: list[int]) -> float:
    """Total SSE across all segments defined by cut indices."""
    boundaries = [0] + list(cuts) + [len(years)]
    return sum(
        _ols_sse(years[boundaries[i]:boundaries[i + 1]],
                 d[boundaries[i]:boundaries[i + 1]])
        for i in range(len(boundaries) - 1)
    )


def _bic(sse: float, n: int, k_params: int) -> float:
    """BIC = n*log(SSE/n) + k*log(n)  (lower is better)."""
    if sse <= 0:
        return -np.inf
    return n * np.log(sse / n) + k_params * np.log(n)


def _exhaustive_search(
    years: np.ndarray,
    d: np.ndarray,
    min_seg: int,
    max_breaks: int,
    penalty: float | None,
) -> list[int]:
    """Return the list of breakpoint indices (into years) that minimise BIC."""
    n = len(years)
    best_bic = _bic(_ols_sse(years, d), n, k_params=2)  # no-break baseline
    best_cuts: list[int] = []

    for n_breaks in range(1, min(max_breaks + 1, n // min_seg)):
        # Generate all candidate cut combinations
        candidates = _candidate_cuts(n, n_breaks, min_seg)
        for cuts in candidates:
            sse = _total_sse(years, d, cuts)
            # k_params: 2 per segment (slope+intercept) + n_breaks
            k = 2 * (n_breaks + 1) + n_breaks
            bic = _bic(sse, n, k)
            if penalty is not None:
                bic = sse + penalty * n_breaks
            if bic < best_bic:
                best_bic = bic
                best_cuts = list(cuts)

    return best_cuts


def _candidate_cuts(n: int, n_breaks: int, min_seg: int):
    """Yield all valid cut-index combinations (combinatorics, small n only)."""
    from itertools import combinations
    valid_positions = range(min_seg, n - min_seg + 1)
    for cuts in combinations(valid_positions, n_breaks):
        # Ensure min_seg between consecutive cuts
        ok = all(cuts[i + 1] - cuts[i] >= min_seg for i in range(len(cuts) - 1))
        ok = ok and (cuts[-1] <= n - min_seg)
        if ok:
            yield cuts


# ---------------------------------------------------------------------------
# PELT fallback (for longer series >20 points)
# ---------------------------------------------------------------------------

def _pelt_on_rates(
    years: np.ndarray, d: np.ndarray, min_seg: int, penalty: float | None
) -> list[int]:
    """Use PELT on first-difference (rate) series for longer time series."""
    import ruptures as rpt
    dt = np.diff(years)
    rates = np.diff(d) / dt
    signal = rates.reshape(-1, 1)
    algo = rpt.Pelt(model="l2", min_size=max(1, min_seg - 1)).fit(signal)
    if penalty is None:
        sigma2 = max(np.var(rates), 1.0)
        penalty = np.log(len(rates)) * sigma2
    raw = algo.predict(pen=penalty)
    # Convert rate-series indices back to distance-series indices
    return [int(i) for i in raw[:-1]]  # drop sentinel


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _split_segments(
    years: np.ndarray, d: np.ndarray, bp_indices: list[int]
) -> list[tuple[np.ndarray, np.ndarray]]:
    cuts = [0] + sorted(bp_indices) + [len(years)]
    return [(years[cuts[i]:cuts[i + 1]], d[cuts[i]:cuts[i + 1]])
            for i in range(len(cuts) - 1)]


def _fit_segments(
    segments: list[tuple[np.ndarray, np.ndarray]],
) -> list[Breakpoint]:
    breakpoints = []
    for i in range(len(segments) - 1):
        x_before, y_before = segments[i]
        x_after, y_after = segments[i + 1]

        rate_before = float(st.linregress(x_before, y_before).slope) if len(x_before) >= 2 else 0.0
        rate_after = float(st.linregress(x_after, y_after).slope) if len(x_after) >= 2 else 0.0

        break_year = float(x_after[0])
        ci_before = _rate_ci(x_before, y_before)
        ci_after = _rate_ci(x_after, y_after)

        breakpoints.append(Breakpoint(
            year=break_year,
            rate_before=rate_before,
            rate_after=rate_after,
            ci_before=ci_before,
            ci_after=ci_after,
        ))
    return breakpoints


def _rate_ci(x: np.ndarray, y: np.ndarray, alpha: float = 0.10) -> tuple[float, float]:
    if len(x) < 3:
        return (0.0, 0.0)
    res = st.linregress(x, y)
    t_crit = st.t.ppf(1 - alpha / 2, df=len(x) - 2)
    return (float(res.slope - t_crit * res.stderr),
            float(res.slope + t_crit * res.stderr))
