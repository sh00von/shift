"""
Monte Carlo positional-uncertainty propagation for rate estimation.

For each transect, perturb each survey position by ±σ (drawn from
N(0, uncertainty)) N times, refit LRR and Sen's slope, and report
empirical 5th–95th percentile CIs.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as st

from shift.models import TransectSeries


def run_montecarlo(
    series_list: list[TransectSeries],
    n: int = 500,
    ci: float = 0.90,
    progress_cb=None,
) -> list[dict]:
    """
    Returns
    -------
    list of dicts, one per transect:
      {
        transect_id,
        lrr_mc_low, lrr_mc_high,   # empirical CI on LRR (m/yr)
        sens_mc_low, sens_mc_high,  # empirical CI on Sen's slope (m/yr)
        n_valid,                    # simulations that succeeded
      }
    """
    alpha = 1.0 - ci
    lo_pct = alpha / 2 * 100
    hi_pct = (1.0 - alpha / 2) * 100

    results = []
    total = len(series_list)

    rng = np.random.default_rng(seed=42)

    for idx, series in enumerate(series_list):
        years = np.array(series.years())
        d_base = np.array(series.distances)
        u = np.array(series.uncertainties)

        lrr_samples: list[float] = []
        sens_samples: list[float] = []

        for _ in range(n):
            noise = rng.normal(0.0, u)
            d_perturbed = d_base + noise

            # LRR via OLS
            try:
                slope, *_ = st.linregress(years, d_perturbed)
                lrr_samples.append(float(slope))
            except Exception:
                pass

            # Sen's slope
            try:
                res = st.theilslopes(d_perturbed, years)
                sens_samples.append(float(res.slope))
            except Exception:
                pass

        def _pct(arr: list[float]):
            if not arr:
                return None, None
            a = np.array(arr)
            return float(np.percentile(a, lo_pct)), float(np.percentile(a, hi_pct))

        lrr_lo, lrr_hi = _pct(lrr_samples)
        sens_lo, sens_hi = _pct(sens_samples)

        results.append({
            "transect_id": series.transect_id,
            "lrr_mc_low": round(lrr_lo, 4) if lrr_lo is not None else None,
            "lrr_mc_high": round(lrr_hi, 4) if lrr_hi is not None else None,
            "sens_mc_low": round(sens_lo, 4) if sens_lo is not None else None,
            "sens_mc_high": round(sens_hi, 4) if sens_hi is not None else None,
            "n_valid": len(lrr_samples),
        })

        if progress_cb and (idx + 1) % max(1, total // 20) == 0:
            progress_cb(f"Monte Carlo: {idx + 1}/{total} transects", (idx + 1) / total)

    return results
