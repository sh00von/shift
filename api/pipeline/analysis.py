"""Transect casting and rate analysis pipeline steps."""
from __future__ import annotations

from typing import Callable

from shift.geometry import cast_transects, intersect_shorelines
from shift.timeseries import build_series
from shift.stats import DSASMethod, EKFMethod

from api.session import Session
from api.pipeline.loaders import load_shorelines, load_baseline

ProgressCB = Callable[[str, float], None]


def preview_transects(state: Session, progress: ProgressCB):
    """Cast transects and store them on the session (no rate analysis)."""
    progress("Loading shorelines…", 0.1)
    shorelines = load_shorelines(state)
    progress("Loading baseline…", 0.3)
    baseline = load_baseline(state, shorelines.crs)
    progress("Casting transects…", 0.6)
    transects = cast_transects(
        baseline,
        spacing=state.spacing,
        smoothing_distance=state.smoothing,
        transect_length=state.transect_length,
        cast_side=state.cast_side,
        shorelines=shorelines,
    )
    state.transects = transects
    progress(f"{len(transects)} transects created.", 1.0)
    return transects


def run_analysis(state: Session, progress: ProgressCB):
    """Full analysis: cast transects, intersect shorelines, fit rate methods."""
    progress("Loading shorelines…", 0.05)
    shorelines = load_shorelines(state)
    progress("Loading baseline…", 0.10)
    baseline = load_baseline(state, shorelines.crs)

    progress("Casting transects…", 0.15)
    transects = cast_transects(
        baseline,
        spacing=state.spacing,
        smoothing_distance=state.smoothing,
        transect_length=state.transect_length,
        cast_side=state.cast_side,
        shorelines=shorelines,
    )
    state.transects = transects

    progress("Computing intersections…", 0.25)
    intersections = intersect_shorelines(transects, shorelines)

    progress("Building time series…", 0.35)
    series_list = build_series(intersections)
    state.series_list = series_list

    results: dict = {}
    n_total = len(series_list)

    if state.run_classic:
        progress(f"Fitting USGS DSAS metrics on {n_total} transects…", 0.45)
        results["classic"] = [DSASMethod().fit(s) for s in series_list]

    if state.run_ekf:
        progress(f"Extended Kalman Filter on {n_total} transects…", 0.60)
        results["ekf"] = [EKFMethod().fit(s) for s in series_list]

    state.results = results
    progress(f"Analysis complete — {n_total} transects processed.", 1.0)
    return series_list, results, transects
