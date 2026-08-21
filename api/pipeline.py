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
from shift.stats import (
    BreakpointMethod,
    DSASMethod,
    RandomForestMethod,
    TheilSenMethod,
    RansacMethod,
)
from shift.forecast import forecast as run_forecast

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

    if state.run_theilsen:
        progress(f"Theil-Sen robust estimator on {n_total} transects…", 0.55)
        m = TheilSenMethod()
        results["theilsen"] = [m.fit(s) for s in series_list]

    if state.run_ransac:
        progress(f"RANSAC robust regression on {n_total} transects…", 0.65)
        m = RansacMethod()
        results["ransac"] = [m.fit(s) for s in series_list]

    if state.run_breakpoint:
        progress(f"Breakpoint regime detection across {n_total} transects…", 0.75)
        m = BreakpointMethod()
        results["breakpoint"] = [m.fit(s) for s in series_list]

    if state.run_rf:
        progress(f"Random Forest benchmark on {n_total} transects…", 0.80)
        m = RandomForestMethod(n_estimators=200, holdout=True)
        rf_results = []
        step = max(1, n_total // 5)
        for i, s in enumerate(series_list):
            rf_results.append(m.fit(s))
            if (i + 1) % step == 0 or (i + 1) == n_total:
                cur = [r.rf_rmse for r in rf_results if r.rf_rmse is not None]
                mean_rmse = np.mean(cur) if cur else 0.0
                p = 0.80 + 0.08 * ((i + 1) / n_total)
                progress(f"Random Forest: {i + 1}/{n_total} (holdout RMSE {mean_rmse:.2f} m)…", p)
        results["rf"] = rf_results

    state.results = results
    # Forecast is NOT auto-generated — the user triggers it explicitly via the
    # Forecast action once rates are computed.
    progress(f"Analysis complete — {n_total} transects processed.", 1.0)
    return series_list, results, transects


def generate_forecast(state: Session, progress: ProgressCB):
    if not state.results or not state.series_list:
        return []

    choice = state.forecast_model or "Breakpoint (Post-break Rate)"
    n_total = len(state.series_list)
    progress(f"Forecasting {state.forecast_horizon} years using {choice}…", 0.3)

    r = state.results
    if "Breakpoint" in choice:
        source = r.get("breakpoint") or r.get("classic") or []
    elif "Theil-Sen" in choice:
        source = r.get("theilsen") or r.get("classic") or []
    elif "RANSAC" in choice:
        source = r.get("ransac") or r.get("classic") or []
    elif "Linear" in choice or "LRR" in choice:
        source = r.get("classic") or []
    elif "Endpoint" in choice or "EPR" in choice:
        source = r.get("classic") or []
    elif "Bayesian" in choice:
        source = r.get("bayesian") or r.get("breakpoint") or []
    elif "Random Forest" in choice:
        source = r.get("rf") or r.get("classic") or []
    else:
        source = r.get("breakpoint") or r.get("classic") or []

    forecast_results = []
    for s, res in zip(state.series_list, source):
        if res is not None:
            forecast_results.append(
                run_forecast(res, s, horizon_years=state.forecast_horizon, ci=state.forecast_ci)
            )
        else:
            forecast_results.append(None)

    state.results["forecast"] = forecast_results
    progress(f"Forecast complete for {n_total} transects.", 1.0)
    return forecast_results


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
