"""Background workers — preview transects and run full analysis pipeline."""
from __future__ import annotations

import traceback

import geopandas as gpd
import pandas as pd
from PySide6.QtCore import QThread, Signal

from shift.geometry import cast_transects, intersect_shorelines
from shift.timeseries import build_series
from shift.stats import BreakpointMethod, ClassicMethod, RandomForestMethod
from shift.forecast import forecast as run_forecast


def _load_shorelines(p: dict) -> gpd.GeoDataFrame:
    shorelines = gpd.read_file(p["shoreline_path"])
    shorelines["date"] = pd.to_datetime(
        shorelines[p["date_col"]], dayfirst=True
    ).dt.date
    unc_col = p.get("uncertainty_col", "")
    if unc_col and unc_col in shorelines.columns:
        shorelines = shorelines.rename(columns={unc_col: "uncertainty"})
    else:
        shorelines["uncertainty"] = p.get("default_uncertainty", 10.0)
    return shorelines


def _load_baseline(p: dict, crs=None) -> gpd.GeoDataFrame:
    baseline = gpd.read_file(p["baseline_path"])
    baseline = baseline.explode(index_parts=False).reset_index(drop=True)
    if crs is not None and baseline.crs != crs:
        baseline = baseline.to_crs(crs)
    return baseline


class PreviewWorker(QThread):
    """Cast transects only — fast preview before full analysis."""
    finished = Signal(object)   # transects GeoDataFrame
    error    = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        try:
            p = self.params
            shorelines = _load_shorelines(p)
            baseline   = _load_baseline(p, shorelines.crs)
            transects  = cast_transects(
                baseline,
                spacing=p["spacing"],
                smoothing_distance=p["smoothing"],
                transect_length=p["transect_length"],
            )
            self.finished.emit(transects)
        except Exception:
            self.error.emit(traceback.format_exc())


class AnalysisWorker(QThread):
    progress = Signal(str)
    finished = Signal(object, object, object)   # series_list, results, transects
    error    = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        try:
            p = self.params

            self.progress.emit("Loading shorelines…")
            shorelines = _load_shorelines(p)

            self.progress.emit("Loading baseline…")
            baseline = _load_baseline(p, shorelines.crs)

            self.progress.emit("Casting transects…")
            transects = cast_transects(
                baseline,
                spacing=p["spacing"],
                smoothing_distance=p["smoothing"],
                transect_length=p["transect_length"],
            )

            self.progress.emit("Computing intersections…")
            intersections = intersect_shorelines(transects, shorelines)

            self.progress.emit("Building time series…")
            series_list = build_series(intersections)

            results = {}

            self.progress.emit("Running classic metrics (EPR / LRR / WLR)…")
            results["classic"] = [ClassicMethod().fit(s) for s in series_list]

            self.progress.emit("Running breakpoint detection…")
            bp_method = BreakpointMethod()
            results["breakpoint"] = [bp_method.fit(s) for s in series_list]

            if p.get("run_bayesian", False):
                self.progress.emit("Running Bayesian changepoint (slow)…")
                from shift.stats import BayesianMethod
                bay = BayesianMethod(n_samples=500, tune=500, chains=2)
                results["bayesian"] = [bay.fit(s) for s in series_list]

            if p.get("run_rf", True):
                self.progress.emit("Running Random Forest benchmark…")
                results["rf"] = [
                    RandomForestMethod(holdout=True).fit(s) for s in series_list
                ]

            if p.get("run_forecast", True):
                self.progress.emit("Computing forecasts…")
                results["forecast"] = [
                    run_forecast(
                        bp_method.fit(s), s,
                        horizon_years=p.get("forecast_horizon", 10)
                    )
                    for s in series_list
                ]

            self.progress.emit("Done.")
            self.finished.emit(series_list, results, transects)

        except Exception:
            self.error.emit(traceback.format_exc())
