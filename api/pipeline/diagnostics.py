"""Diagnostics pipeline: Monte Carlo CI, CBC classification, spatial autocorrelation."""
from __future__ import annotations

from typing import Callable

from shift.stats.spatial import morans_i, smooth_rates
from shift.stats.cbc import classify_all
from shift.validation.montecarlo import run_montecarlo as _run_mc

from api.session import Session

ProgressCB = Callable[[str, float], None]


def run_montecarlo(state: Session, progress: ProgressCB):
    """Perturb survey positions N=500 times and compute empirical CIs."""
    if not state.series_list:
        raise ValueError("Run analysis first.")
    results = _run_mc(
        state.series_list,
        n=500,
        ci=state.forecast_ci,
        progress_cb=progress,
    )
    state.mc_results = results
    progress(f"Monte Carlo complete — {len(results)} transects.", 1.0)
    return results


def run_cbc(state: Session, progress: ProgressCB):
    """Classify each transect's coastal behaviour (6-class CBC)."""
    if not state.series_list:
        raise ValueError("Run analysis first.")
    progress("Classifying coastal behaviour…", 0.1)
    results = classify_all(state.series_list)
    state.cbc_results = results
    progress(f"CBC complete — {len(results)} transects classified.", 1.0)
    return results


def compute_spatial(state: Session, window: int | None = None) -> dict:
    """Compute Moran's I and smoothed LRR rates for the current results."""
    if not state.results or not state.series_list:
        return {}
    w = window if window is not None else state.spatial_smooth_window
    classic = state.results.get("classic", [])
    tids = [s.transect_id for s in state.series_list]
    rates = [r.lrr if r else None for r in classic]
    mi = morans_i(rates)
    smoothed = smooth_rates(tids, rates, window=w)
    return {"morans": mi, "smoothed": smoothed}
