"""Export endpoints: CSV, GeoJSON, and ZIP bundle."""
from __future__ import annotations

import datetime
import io
import json
import zipfile

import geopandas as gpd
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api import geojson as gj
from api import serialize
from api.deps import params, require
from api.session import Session

router = APIRouter()


def _full_rates_df(s: Session) -> pd.DataFrame:
    r = s.results or {}
    classic = r.get("classic", [])
    ekf = r.get("ekf", [])
    rows = []
    for i, ser in enumerate(s.series_list):
        cl = classic[i] if i < len(classic) else None
        ek = ekf[i] if i < len(ekf) else None
        years = ser.years()
        n_pts = len(ser)
        t_span = round(years[-1] - years[0], 2) if n_pts >= 2 else 0.0
        rows.append({
            "transect_id": int(ser.transect_id),
            "n_surveys": n_pts,
            "time_span_years": t_span,
            "earliest_year": round(years[0], 3) if years else None,
            "latest_year": round(years[-1], 3) if years else None,
            "epr_m_yr": round(cl.epr, 3) if cl and cl.epr is not None else None,
            "lrr_m_yr": round(cl.lrr, 3) if cl and cl.lrr is not None else None,
            "lrr_ci_low_m_yr": round(cl.lrr_ci_low, 3) if cl and cl.lrr_ci_low is not None else None,
            "lrr_ci_high_m_yr": round(cl.lrr_ci_high, 3) if cl and cl.lrr_ci_high is not None else None,
            "lrr_significant": cl.lrr_significant if cl else None,
            "wlr_m_yr": round(cl.wlr, 3) if cl and cl.wlr is not None else None,
            "nsm_m": round(cl.nsm, 2) if cl and cl.nsm is not None else None,
            "sce_m": round(cl.sce, 2) if cl and cl.sce is not None else None,
            "ekf_m_yr": round(ek.ekf, 3) if ek and ek.ekf is not None else None,
        })
    return pd.DataFrame(rows)


def _intersections_df(s: Session) -> pd.DataFrame:
    rows = []
    for ser in s.series_list:
        for idx, (dt, dist, unc) in enumerate(zip(ser.dates, ser.distances, ser.uncertainties)):
            dec_yr = dt.year + (dt.timetuple().tm_yday - 1) / 365.25
            rows.append({
                "transect_id": int(ser.transect_id),
                "survey_index": idx + 1,
                "calendar_date": dt.strftime("%Y-%m-%d"),
                "decimal_year": round(dec_yr, 4),
                "distance_from_baseline_m": round(dist, 3),
                "uncertainty_m": round(unc, 2),
            })
    return pd.DataFrame(rows)


def _readme(s: Session) -> str:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_tr = len(s.series_list)
    return f"""================================================================================
SHIFT GIS Analysis & Export Package
================================================================================
Generated: {now_str}
Session ID: {s.id}
Dataset: {s.shoreline_filename or "Survey Shorelines"}
Baseline: {s.baseline_filename or "Offshore Baseline"}
Projected CRS: {s.transects.crs if s.transects is not None else "EPSG:32646"}

SUMMARY CONFIGURATION:
--------------------------------------------------------------------------------
Total Cast Transects: {n_tr}
Transect Spacing: {s.spacing} m
Smoothing Window: {s.smoothing} m
Cast Reach Length: {s.transect_length} m
Cast Direction: {s.cast_side.upper()} of baseline
Date Column: {s.date_col} (Format: {s.date_format})
Uncertainty Channel: {s.uncertainty_col or f"Fixed Default (±{s.default_uncertainty} m)"}

INCLUDED DATA PRODUCTS:
--------------------------------------------------------------------------------
1. shift_transect_rates.csv - EPR, LRR, WLR, NSM, SCE, EKF per transect
2. transects_rates_envelope.geojson - Clipped rate-coloured transect lines
3. transects_full.geojson - Full-length orthogonal transects
4. intersections_raw.csv - Per-transect measurement series
5. baseline.geojson & shorelines.geojson - Input layers in WGS84
6. forecast_shoreline.geojson & forecast_uncertainty_cone.geojson (if generated)
7. session_config.json - Run configuration and metadata

CITATION:
--------------------------------------------------------------------------------
SHIFT: Automated Shoreline Change Analysis Workbench
Built with Python (GeoPandas, Shapely) & Next.js / Leaflet.
================================================================================
"""


@router.get("/session/{sid}/export/csv")
def export_csv(sid: str):
    s = require(sid)
    if not s.results:
        raise HTTPException(status_code=400, detail="No results to export.")
    csv = _full_rates_df(s).to_csv(index=False)
    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=shift_transect_rates.csv"})


@router.get("/session/{sid}/export/intersections.csv")
def export_intersections(sid: str):
    s = require(sid)
    if not s.series_list:
        raise HTTPException(status_code=400, detail="No shoreline intersections to export.")
    csv = _intersections_df(s).to_csv(index=False)
    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=shift_intersections_raw.csv"})


@router.get("/session/{sid}/export/transects.geojson")
def export_transects(sid: str):
    s = require(sid)
    if s.transects is None:
        raise HTTPException(status_code=400, detail="No transects to export.")
    return Response(content=s.transects.to_crs("EPSG:4326").to_json(),
                    media_type="application/geo+json",
                    headers={"Content-Disposition": "attachment; filename=shift_transects_full.geojson"})


@router.get("/session/{sid}/export/transects_rates.geojson")
def export_transects_rates(sid: str):
    s = require(sid)
    if not s.results or s.transects is None:
        raise HTTPException(status_code=400, detail="No analysis results to export.")
    ch = gj.rate_choropleth(s)
    return Response(content=json.dumps(ch.get("geojson", {"type": "FeatureCollection", "features": []})),
                    media_type="application/geo+json",
                    headers={"Content-Disposition": "attachment; filename=shift_transects_rates_envelope.geojson"})


@router.get("/session/{sid}/export/forecast.geojson")
def export_forecast(sid: str):
    s = require(sid)
    fc = gj.forecast_geojson(s)
    if not fc.get("line"):
        raise HTTPException(status_code=400, detail="No forecast generated.")
    return Response(content=json.dumps(fc["line"]), media_type="application/geo+json",
                    headers={"Content-Disposition": "attachment; filename=shift_forecast_shoreline.geojson"})


@router.get("/session/{sid}/export/bundle.zip")
def export_bundle(sid: str):
    s = require(sid)
    if not s.results and s.transects is None and not s.shoreline_path:
        raise HTTPException(status_code=400, detail="No session data to export.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", _readme(s))
        z.writestr("session_config.json", json.dumps(params(s), indent=2))
        if s.results:
            z.writestr("shift_transect_rates.csv", _full_rates_df(s).to_csv(index=False))
        if s.series_list:
            z.writestr("intersections_raw.csv", _intersections_df(s).to_csv(index=False))
        if s.results and s.transects is not None:
            ch = gj.rate_choropleth(s)
            z.writestr("transects_rates_envelope.geojson", json.dumps(ch.get("geojson", {}), indent=2))
        if s.transects is not None:
            z.writestr("transects_full.geojson", s.transects.to_crs("EPSG:4326").to_json())
        if s.baseline_path:
            try:
                z.writestr("baseline.geojson", gpd.read_file(s.baseline_path).to_crs("EPSG:4326").to_json())
            except Exception:
                pass
        if s.shoreline_path:
            try:
                z.writestr("shorelines.geojson", gpd.read_file(s.shoreline_path).to_crs("EPSG:4326").to_json())
            except Exception:
                pass
        if s.results and s.results.get("forecast"):
            fc = gj.forecast_geojson(s)
            if fc.get("line"):
                z.writestr("forecast_shoreline.geojson", json.dumps(fc["line"], indent=2))
            if fc.get("ribbon"):
                z.writestr("forecast_uncertainty_cone.geojson", json.dumps(fc["ribbon"], indent=2))
        if s.aln2d_erosion is not None and not s.aln2d_erosion.empty:
            z.writestr("processed_erosion_polygons.geojson", json.dumps(gj.aln2d_erosion_geojson(s), indent=2))
        if s.aln2d_accretion is not None and not s.aln2d_accretion.empty:
            z.writestr("processed_accretion_polygons.geojson", json.dumps(gj.aln2d_accretion_geojson(s), indent=2))
        if s.aln2d_reaches is not None and not s.aln2d_reaches.empty:
            reaches_gj = gj.aln2d_reaches_geojson(s)
            z.writestr("processed_linear_reach_rates.geojson", json.dumps(reaches_gj.get("geojson", {}), indent=2))
            df_r = pd.DataFrame(serialize.aln2d_reach_rows(s))
            if not df_r.empty:
                z.writestr("processed_linear_reach_rates.csv", df_r.to_csv(index=False))
        if s.aln2d_summary is not None and not s.aln2d_summary.empty:
            z.writestr("morphodynamic_budget_summary.csv", pd.DataFrame(serialize.aln2d_summary_rows(s)).to_csv(index=False))
        if s.aln2d_validation is not None and not s.aln2d_validation.empty:
            z.writestr("statistical_validation_matrix.csv", pd.DataFrame(serialize.aln2d_validation_rows(s)).to_csv(index=False))

    buf.seek(0)
    now_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename=shift_gis_bundle_{now_tag}.zip"})
