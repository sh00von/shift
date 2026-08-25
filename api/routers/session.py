"""Session lifecycle, params, field mapping, and upload endpoints."""
from __future__ import annotations

import os
import tempfile

import geopandas as gpd
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile

from api import pipeline
from api.deps import FieldMappingRequest, ParamPatch, log, params, require
from api.session import store

router = APIRouter()


@router.post("/session")
def create_session():
    s = store.create()
    return {"session_id": s.id, "params": params(s)}


@router.get("/session/{sid}/params")
def get_params(sid: str):
    return params(require(sid))


@router.patch("/session/{sid}/params")
def patch_params(sid: str, patch: ParamPatch):
    s = require(sid)
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    return params(s)


@router.post("/session/{sid}/clear")
def clear_session(sid: str):
    s = require(sid)
    s.shoreline_path = s.baseline_path = None
    s.shoreline_filename = s.baseline_filename = ""
    s.transects = None
    s.series_list = []
    s.results = {}
    log(s, "Session cleared.")
    return params(s)


def _shoreline_preview(s):
    if not s.shoreline_path or not os.path.exists(s.shoreline_path):
        return {
            "has_shoreline": False, "filename": "", "columns": [], "date_col": "",
            "date_format": "auto", "uncertainty_col": None, "default_uncertainty": 10.0,
            "preview_rows": [], "detected_years": [],
        }
    gdf = gpd.read_file(s.shoreline_path)
    cols = [c for c in gdf.columns if c != "geometry"]
    date_col = s.date_col or next(
        (c for c in cols if any(k in c.lower() for k in ["date", "year", "time", "yr"])),
        cols[0] if cols else "",
    )
    date_fmt = s.date_format or "auto"
    parsed_dates = (
        pipeline.parse_dates(gdf[date_col], date_fmt)
        if date_col and date_col in gdf.columns
        else pd.Series([None] * len(gdf))
    )
    unique_years = sorted({d.year for d in parsed_dates if d is not None})
    rows = []
    for idx, row in gdf.head(20).iterrows():
        raw_d = row.get(date_col) if date_col in gdf.columns else ""
        p_d = parsed_dates.iloc[idx] if idx < len(parsed_dates) else None
        raw_u = row.get(s.uncertainty_col) if (s.uncertainty_col and s.uncertainty_col in gdf.columns) else None
        try:
            p_u = float(raw_u) if raw_u is not None and not pd.isna(raw_u) else s.default_uncertainty
        except (ValueError, TypeError):
            p_u = s.default_uncertainty
        rows.append({
            "index": int(idx),
            "raw_date": str(raw_d) if raw_d is not None else "",
            "parsed_date": p_d.strftime("%Y-%m-%d") if p_d else "Invalid Date",
            "parsed_year": p_d.year if p_d else None,
            "raw_uncertainty": str(raw_u) if raw_u is not None and not pd.isna(raw_u) else "(Default)",
            "parsed_uncertainty": round(p_u, 2),
        })
    return {
        "has_shoreline": True, "filename": s.shoreline_filename, "columns": cols,
        "date_col": date_col, "date_format": date_fmt, "uncertainty_col": s.uncertainty_col,
        "default_uncertainty": s.default_uncertainty, "preview_rows": rows, "detected_years": unique_years,
    }


@router.get("/session/{sid}/shoreline/fields")
def get_shoreline_fields(sid: str):
    return _shoreline_preview(require(sid))


@router.post("/session/{sid}/shoreline/fields")
def set_shoreline_fields(sid: str, req: FieldMappingRequest):
    s = require(sid)
    s.date_col = req.date_col
    s.date_format = req.date_format or "auto"
    s.default_uncertainty = max(0.1, float(req.default_uncertainty))
    if req.create_uncertainty_col and s.shoreline_path and os.path.exists(s.shoreline_path):
        try:
            gdf = gpd.read_file(s.shoreline_path)
            new_col = req.create_uncertainty_col.strip()
            if new_col:
                gdf[new_col] = float(s.default_uncertainty)
                gdf.to_file(s.shoreline_path, driver="GeoJSON")
                s.uncertainty_col = new_col
                log(s, f"Created uncertainty column '{new_col}' with default ±{s.default_uncertainty}m")
        except Exception as e:
            log(s, f"Could not create uncertainty column: {e}", "WARNING")
    else:
        s.uncertainty_col = req.uncertainty_col if req.uncertainty_col else None
    log(s, f"Field mapping updated: date='{s.date_col}' (format={s.date_format}), uncertainty='{s.uncertainty_col or 'Default ' + str(s.default_uncertainty) + 'm'}'")
    return _shoreline_preview(s)


async def _save_upload(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename or "layer.geojson")[1].lower() or ".geojson"
    if suffix in [".shp", ".dbf", ".shx", ".prj"]:
        raise HTTPException(
            status_code=400,
            detail="Shapefiles (.shp) are not supported. SHIFT standardises exclusively on standard GeoJSON (.geojson / .json) files.",
        )
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(await file.read())
    tmp.close()
    return tmp.name


@router.post("/session/{sid}/upload/shoreline")
async def upload_shoreline(sid: str, file: UploadFile):
    s = require(sid)
    path = await _save_upload(file)
    try:
        gdf = gpd.read_file(path)
        cols = [c for c in gdf.columns if c != "geometry"]
        date_cand = next((c for c in cols if any(k in c.lower() for k in ["date", "year", "time", "yr"])), cols[0] if cols else "")
        unc_cand = next((c for c in cols if any(k in c.lower() for k in ["unc", "err", "std", "sigma"])), None)
        s.shoreline_path = path
        s.shoreline_filename = file.filename or "shoreline.geojson"
        s.date_col = date_cand
        s.uncertainty_col = unc_cand
        log(s, f"Shoreline loaded: {s.shoreline_filename} ({len(gdf)} features, CRS {gdf.crs})")
        return {"filename": s.shoreline_filename, "n_features": len(gdf), "columns": cols, "date_col": date_cand, "uncertainty_col": unc_cand}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/session/{sid}/upload/baseline")
async def upload_baseline(sid: str, file: UploadFile):
    s = require(sid)
    path = await _save_upload(file)
    try:
        gdf = gpd.read_file(path)
        s.baseline_path = path
        s.baseline_filename = file.filename or "baseline.geojson"
        log(s, f"Baseline loaded: {s.baseline_filename} ({len(gdf)} features)")
        return {"filename": s.baseline_filename, "n_features": len(gdf)}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/session/{sid}/demo")
def load_demo(sid: str):
    s = require(sid)
    custom_sl = r"D:\thesis-work\shore-geojson\demo_shorelines.geojson"
    custom_bl = r"D:\thesis-work\shore-geojson\demo_baseline.geojson"
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_sl = os.path.join(root_dir, "sample_data", "demo_shorelines.geojson")
    bundled_bl = os.path.join(root_dir, "sample_data", "demo_baseline.geojson")

    if os.path.exists(custom_sl) and os.path.exists(custom_bl):
        sl_path, bl_path = custom_sl, custom_bl
        sl_fname, bl_fname = "demo_shorelines.geojson", "demo_baseline.geojson"
    elif os.path.exists(bundled_sl) and os.path.exists(bundled_bl):
        sl_path, bl_path = bundled_sl, bundled_bl
        sl_fname, bl_fname = "demo_shorelines.geojson", "demo_baseline.geojson"
    else:
        out_dir = os.path.join(tempfile.gettempdir(), "shift_sample")
        sl_path = os.path.join(out_dir, "demo_shorelines.geojson")
        bl_path = os.path.join(out_dir, "demo_baseline.geojson")
        if not (os.path.exists(sl_path) and os.path.exists(bl_path)):
            sl_path, bl_path = pipeline.generate_sample_data(out_dir)
        sl_fname, bl_fname = "demo_shorelines.geojson", "demo_baseline.geojson"

    s.shoreline_path = sl_path
    s.baseline_path = bl_path
    s.shoreline_filename = sl_fname
    s.baseline_filename = bl_fname
    gdf_sl = gpd.read_file(sl_path)
    cols = [c for c in gdf_sl.columns if c != "geometry"]
    date_cand = next((c for c in cols if any(k in c.lower() for k in ["date", "year", "time", "yr"])), cols[0] if cols else "date")
    unc_cand = next((c for c in cols if any(k in c.lower() for k in ["unc", "err", "std", "sigma"])), None)
    s.date_col = date_cand
    s.uncertainty_col = unc_cand
    log(s, f"Demo dataset loaded: {sl_fname} ({len(gdf_sl)} shorelines) and {bl_fname}.")
    return {
        "shoreline": {"filename": s.shoreline_filename, "n_features": len(gdf_sl), "columns": cols, "date_col": date_cand, "uncertainty_col": unc_cand},
        "baseline": {"filename": s.baseline_filename, "n_features": len(gpd.read_file(bl_path))},
    }


@router.post("/session/{sid}/auto-baseline")
def auto_baseline(sid: str):
    s = require(sid)
    if not s.shoreline_path:
        raise HTTPException(status_code=400, detail="Load shorelines first.")
    try:
        sl = gpd.read_file(s.shoreline_path)
        bl = pipeline.create_synthetic_baseline(sl, buffer_distance=s.buffer_distance)
        tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        tmp.close()
        bl.to_crs("EPSG:4326").to_file(tmp.name, driver="GeoJSON")
        s.baseline_path = tmp.name
        s.baseline_filename = "auto_baseline.geojson"
        log(s, f"Auto-baseline constructed ({s.buffer_distance}m buffer).")
        return {"filename": s.baseline_filename, "n_features": len(bl)}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))
