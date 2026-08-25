"""Analysis pipeline — wraps the shift library. Ported from web/tasks.py but
decoupled from NiceGUI. Progress is reported through a simple callback that the
WebSocket layer forwards to the browser."""
from __future__ import annotations

import warnings
from typing import Callable

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message=".*R\\^2 score is not well-defined.*")
warnings.filterwarnings("ignore", message=".*UndefinedMetricWarning.*")

from shift.geometry import cast_transects, intersect_shorelines
from shift.timeseries import build_series
from shift.stats import DSASMethod, EKFMethod, arima_forecast, holt_forecast, polynomial_forecast, logarithmic_forecast
from shift.stats.spatial import morans_i, smooth_rates
from shift.stats.cbc import classify_all, LABEL_COLORS
from shift.forecast import forecast as run_forecast
from shift.forecast import kalman_forecast as run_kalman_forecast
from shift.validation import evaluate_forecasts
from shift.validation.montecarlo import run_montecarlo as _run_mc
from shift.aln2d import ALN2DEngine


from api.session import Session

ProgressCB = Callable[[str, float], None]




def parse_dates(series: pd.Series, date_format: str = "auto") -> pd.Series:
    """Robust date parser supporting auto-detection, custom formats, integer years, and regex fallback."""
    s_clean = series.copy()
    if pd.api.types.is_numeric_dtype(s_clean):
        if (s_clean.dropna().between(1800, 2200)).all():
            return pd.to_datetime(s_clean.astype(int).astype(str) + "-01-01", errors="coerce").dt.date

    s_str = s_clean.astype(str).str.strip()

    if date_format and date_format.lower() != "auto":
        fmt = date_format.strip()
        if fmt.upper() in ["YYYY", "%Y"]:
            years = s_str.str.extract(r"(\d{4})")[0]
            return pd.to_datetime(years + "-01-01", errors="coerce").dt.date
        if fmt.upper() in ["DD/MM/YYYY", "%D/%M/%Y"]:
            fmt = "%d/%m/%Y"
        elif fmt.upper() in ["YYYY-MM-DD", "%Y-%M-%D"]:
            fmt = "%Y-%m-%d"
        elif fmt.upper() in ["MM/DD/YYYY", "%M/%D/%Y"]:
            fmt = "%m/%d/%Y"
        elif fmt.upper() in ["DD-MM-YYYY"]:
            fmt = "%d-%m-%Y"
        try:
            parsed = pd.to_datetime(s_str, format=fmt, errors="coerce")
            if parsed.notnull().any():
                return parsed.dt.date
        except Exception:
            pass

    try:
        dt = pd.to_datetime(s_str, dayfirst=True, errors="coerce")
        if dt.notnull().sum() >= len(s_str) * 0.5:
            return dt.dt.date
    except Exception:
        pass

    try:
        dt = pd.to_datetime(s_str, dayfirst=False, errors="coerce")
        if dt.notnull().sum() >= len(s_str) * 0.5:
            return dt.dt.date
    except Exception:
        pass

    years = s_str.str.extract(r"(\d{4})")[0]
    return pd.to_datetime(years + "-01-01", errors="coerce").dt.date


def _load_shorelines(state: Session) -> gpd.GeoDataFrame:
    sl = gpd.read_file(state.shoreline_path)
    date_col = state.date_col or next((c for c in sl.columns if any(k in c.lower() for k in ["date", "year", "time", "yr"])), sl.columns[0])
    sl["date"] = parse_dates(sl[date_col], state.date_format)
    unc_col = state.uncertainty_col or ""
    if unc_col and unc_col in sl.columns:
        sl = sl.rename(columns={unc_col: "uncertainty"})
    elif "Uncertainty" in sl.columns:
        sl = sl.rename(columns={"Uncertainty": "uncertainty"})
    elif "uncertainty" not in sl.columns:
        sl["uncertainty"] = state.default_uncertainty

    if sl.crs is None:
        sl = sl.set_crs("EPSG:4326")
    if sl.crs.is_geographic:
        sl = sl.to_crs(sl.estimate_utm_crs())
    return sl


def _load_baseline(state: Session, crs) -> gpd.GeoDataFrame:
    bl = gpd.read_file(state.baseline_path)
    bl = bl.explode(index_parts=False).reset_index(drop=True)
    if bl.crs is None:
        bl = bl.set_crs("EPSG:4326")
    if crs is not None and bl.crs != crs:
        bl = bl.to_crs(crs)
    return bl


def preview_transects(state: Session, progress: ProgressCB):
    progress("Loading shorelines…", 0.1)
    shorelines = _load_shorelines(state)
    progress("Loading baseline…", 0.3)
    baseline = _load_baseline(state, shorelines.crs)
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
    progress("Loading shorelines…", 0.05)
    shorelines = _load_shorelines(state)
    progress("Loading baseline…", 0.10)
    baseline = _load_baseline(state, shorelines.crs)

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
        m = DSASMethod()
        results["classic"] = [m.fit(s) for s in series_list]

    if state.run_ekf:
        progress(f"Extended Kalman Filter on {n_total} transects…", 0.60)
        m = EKFMethod()
        results["ekf"] = [m.fit(s) for s in series_list]

    state.results = results

    progress(f"Analysis complete — {n_total} transects processed.", 1.0)
    return series_list, results, transects


def run_aln2d(state: Session, progress: ProgressCB):
    """Executes 2D Areal-to-Linear Normalization and 2D-ALN Engine."""
    import os
    if not state.shoreline_path or not os.path.exists(state.shoreline_path):
        raise ValueError("No shoreline dataset loaded in current session.")

    progress("2D-ALN: Loading shoreline layers…", 0.05)
    shorelines = gpd.read_file(state.shoreline_path)

    baseline = None
    if state.baseline_path and os.path.exists(state.baseline_path):
        baseline = gpd.read_file(state.baseline_path)

    engine = ALN2DEngine(
        reach_length_meters=state.aln2d_reach_length,
        reach_buffer_meters=state.aln2d_reach_buffer,
        search_mask_buffer_meters=state.aln2d_search_mask_buffer,
    )

    out = engine.run(
        shorelines=shorelines,
        date_col=state.date_col,
        date_format=state.date_format,
        baseline=baseline,
        progress=progress,
    )

    state.aln2d_erosion = out["erosion_gdf"]
    state.aln2d_accretion = out["accretion_gdf"]
    state.aln2d_reaches = out["reach_gdf"]
    state.aln2d_summary = out["summary_df"]
    state.aln2d_validation = out["validation_df"]

    progress("2D-ALN: 2D-ALN Analysis successfully completed.", 1.0)
    return out



def generate_forecast(state: Session, progress: ProgressCB):
    """Run all selected forecast models and evaluate each with a hindcast."""
    if not state.results or not state.series_list:
        return {}

    models = state.forecast_models or ["Kalman Filter (DSAS)"]
    n_total = len(state.series_list)
    r = state.results
    all_forecasts: dict = {}

    for idx, model in enumerate(models):
        base_prog = 0.05 + 0.55 * idx / len(models)
        progress(f"Forecasting {state.forecast_horizon} yr — {model}…", base_prog)
        fc_list = []

        if "Kalman" in model:
            source = r.get("classic") or r.get("ekf") or []
            for s, res in zip(state.series_list, source):
                fc_list.append(
                    run_kalman_forecast(res, s, horizon_years=state.forecast_horizon, ci=state.forecast_ci)
                    if res is not None else None
                )
        elif "ARIMA" in model:
            for s in state.series_list:
                fc_list.append(arima_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Holt" in model:
            for s in state.series_list:
                fc_list.append(holt_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Polynomial" in model:
            for s in state.series_list:
                fc_list.append(polynomial_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "Logarithmic" in model:
            for s in state.series_list:
                fc_list.append(logarithmic_forecast(s, horizon_years=state.forecast_horizon, ci=state.forecast_ci))
        elif "EKF" in model:
            source = r.get("ekf") or r.get("classic") or []
            for s, res in zip(state.series_list, source):
                fc_list.append(
                    run_forecast(res, s, horizon_years=state.forecast_horizon, ci=state.forecast_ci)
                    if res is not None else None
                )
        else:
            fc_list = [None] * len(state.series_list)

        all_forecasts[model] = fc_list

    # Use first model as the primary map layer; reset the active display model.
    primary = all_forecasts.get(models[0], [])
    state.results["forecast"] = primary
    state.results["forecasts"] = all_forecasts
    state.forecast_model = models[0]

    # Hindcast evaluation — tells user which forecast model is most accurate
    progress("Running hindcast evaluation across forecast models…", 0.65)
    eval_result = evaluate_forecasts(state.series_list, models, progress=lambda m, p: progress(m, 0.65 + 0.30 * p))
    state.forecast_eval = eval_result

    progress(f"Forecast complete — {len(models)} model(s), {n_total} transects.", 1.0)
    return all_forecasts



def run_montecarlo(state: Session, progress: ProgressCB):
    """Perturb shoreline positions N=500 times and compute empirical CIs."""
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
    """Classify each transect's behaviour (6-class CBC)."""
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


# ── Synthetic helpers (auto-baseline + demo data) ───────────────────────────

def create_synthetic_baseline(shorelines: gpd.GeoDataFrame, buffer_distance: float) -> gpd.GeoDataFrame:
    """Build an offset baseline by buffering the earliest shoreline seaward."""
    from shapely.ops import unary_union
    from shapely.geometry import LineString, MultiLineString, LinearRing

    sl = shorelines.copy()
    sl = sl[~sl.geometry.is_empty & sl.geometry.notna()]
    if len(sl) == 0:
        raise ValueError("Shoreline layer contains no valid geometries.")

    if sl.crs is None:
        sl = sl.set_crs("EPSG:4326")
    if sl.crs.is_geographic:
        try:
            utm_crs = sl.estimate_utm_crs()
            sl = sl.to_crs(utm_crs)
        except Exception:
            sl = sl.to_crs("EPSG:3857")

    geoms = [g for g in sl.geometry.values if g is not None and not g.is_empty]
    if not geoms:
        raise ValueError("Shoreline layer contains no valid geometries.")

    merged = unary_union(geoms)
    buf = merged.buffer(float(buffer_distance))
    boundary = buf.boundary

    lines = []
    if boundary.geom_type in ("LineString", "LinearRing"):
        lines.append(boundary)
    elif hasattr(boundary, "geoms"):
        for g in boundary.geoms:
            if g.geom_type in ("LineString", "LinearRing") and not g.is_empty:
                lines.append(g)

    if not lines:
        raise ValueError("Could not derive a baseline boundary from shoreline buffer.")

    longest = max(lines, key=lambda g: g.length)
    final_line = LineString(list(longest.coords))

    return gpd.GeoDataFrame({"name": ["auto_baseline"]}, geometry=[final_line], crs=sl.crs)


def generate_sample_data(out_dir: str) -> tuple[str, str]:
    """Generate a synthetic multi-decadal eroding coastline + baseline (EPSG:4326)."""
    import os
    from shapely.geometry import LineString

    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(42)

    # Base coastline along ~90.6E, 22.5N, sinuous NS line.
    n_pts = 60
    lat = np.linspace(22.40, 22.62, n_pts)
    base_lon = 90.60 + 0.010 * np.sin(np.linspace(0, 3 * np.pi, n_pts))

    years = [1990, 1998, 2005, 2011, 2018, 2023]
    # metres-per-degree-lon at this latitude (~103 km/deg)
    m_per_deg = 111_320 * np.cos(np.deg2rad(22.5))

    feats = []
    for yr in years:
        dt = yr - 1990
        # progressive erosion (shoreline retreats landward = +lon here) with noise
        retreat_m = -12.0 * dt + rng.normal(0, 8.0, n_pts).cumsum() * 0.15
        lon = base_lon - (retreat_m / m_per_deg)
        feats.append({
            "date": f"{yr}-06-15",
            "uncertainty": float(rng.uniform(5, 12)),
            "geometry": LineString(np.column_stack([lon, lat])),
        })

    sl = gpd.GeoDataFrame(feats, crs="EPSG:4326")
    sl_path = os.path.join(out_dir, "sample_shorelines.geojson")
    sl.to_file(sl_path, driver="GeoJSON")

    bl = create_synthetic_baseline(sl, buffer_distance=500.0).to_crs("EPSG:4326")
    bl_path = os.path.join(out_dir, "sample_baseline.geojson")
    bl.to_file(bl_path, driver="GeoJSON")

    return sl_path, bl_path
