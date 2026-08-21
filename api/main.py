"""SHIFT FastAPI application — REST + WebSocket API wrapping the shift library.

Run with:  uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import datetime
import io
import json
import os
import tempfile
import traceback
import warnings
import zipfile

import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

warnings.filterwarnings("ignore")

from api import geojson as gj
from api import pipeline, serialize
from api.session import Session, store

app = FastAPI(title="SHIFT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require(sid: str) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found. Create a new session.")
    return s


def _log(state: Session, msg: str, level: str = "INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    state.logs.append(f"[{ts}] [{level}] {msg}")


# ── Session lifecycle ───────────────────────────────────────────────────────

@app.post("/api/session")
def create_session():
    s = store.create()
    return {"session_id": s.id, "params": _params(s)}


def _params(s: Session) -> dict:
    return {
        "spacing": s.spacing, "smoothing": s.smoothing, "transect_length": s.transect_length,
        "cast_side": s.cast_side, "buffer_distance": s.buffer_distance,
        "default_uncertainty": s.default_uncertainty,
        "run_classic": s.run_classic, "run_theilsen": s.run_theilsen, "run_ransac": s.run_ransac,
        "run_breakpoint": s.run_breakpoint, "run_rf": s.run_rf,
        "forecast_model": s.forecast_model, "forecast_horizon": s.forecast_horizon,
        "forecast_ci": s.forecast_ci, "style_metric": s.style_metric, "color_ramp": s.color_ramp,
        "shoreline_palette": s.shoreline_palette,
        "date_col": s.date_col, "date_format": s.date_format, "uncertainty_col": s.uncertainty_col,
        "shoreline_filename": s.shoreline_filename, "baseline_filename": s.baseline_filename,
        "has_shoreline": s.shoreline_path is not None, "has_baseline": s.baseline_path is not None,
        "has_results": bool(s.results), "logs": s.logs[-100:],
    }


class ParamPatch(BaseModel):
    spacing: float | None = None
    smoothing: float | None = None
    transect_length: float | None = None
    cast_side: str | None = None
    buffer_distance: float | None = None
    default_uncertainty: float | None = None
    run_classic: bool | None = None
    run_theilsen: bool | None = None
    run_ransac: bool | None = None
    run_breakpoint: bool | None = None
    run_rf: bool | None = None
    forecast_model: str | None = None
    forecast_horizon: int | None = None
    forecast_ci: float | None = None
    style_metric: str | None = None
    color_ramp: str | None = None
    shoreline_palette: str | None = None
    date_col: str | None = None
    date_format: str | None = None
    uncertainty_col: str | None = None


class FieldMappingRequest(BaseModel):
    date_col: str
    date_format: str = "auto"
    uncertainty_col: str | None = None
    default_uncertainty: float = 10.0
    create_uncertainty_col: str | None = None


def _build_shoreline_preview(s: Session):
    if not s.shoreline_path or not os.path.exists(s.shoreline_path):
        return {
            "has_shoreline": False, "filename": "", "columns": [], "date_col": "",
            "date_format": "auto", "uncertainty_col": None, "default_uncertainty": 10.0,
            "preview_rows": [], "detected_years": [],
        }
    gdf = gpd.read_file(s.shoreline_path)
    cols = [c for c in gdf.columns if c != "geometry"]
    date_col = s.date_col or next((c for c in cols if any(k in c.lower() for k in ["date", "year", "time", "yr"])), (cols[0] if cols else ""))
    unc_col = s.uncertainty_col
    date_fmt = s.date_format or "auto"

    parsed_dates = pipeline.parse_dates(gdf[date_col], date_fmt) if (date_col and date_col in gdf.columns) else pd.Series([None] * len(gdf))

    unique_years = sorted(list({d.year for d in parsed_dates if d is not None}))

    rows = []
    for idx, row in gdf.head(20).iterrows():
        raw_d = row.get(date_col) if date_col in gdf.columns else ""
        p_d = parsed_dates.iloc[idx] if idx < len(parsed_dates) else None
        p_yr = p_d.year if p_d else None

        raw_u = row.get(unc_col) if (unc_col and unc_col in gdf.columns) else None
        try:
            p_u = float(raw_u) if raw_u is not None and not pd.isna(raw_u) else s.default_uncertainty
        except (ValueError, TypeError):
            p_u = s.default_uncertainty

        rows.append({
            "index": int(idx),
            "raw_date": str(raw_d) if raw_d is not None else "",
            "parsed_date": p_d.strftime("%Y-%m-%d") if p_d else "Invalid Date",
            "parsed_year": p_yr,
            "raw_uncertainty": str(raw_u) if raw_u is not None and not pd.isna(raw_u) else "(Default)",
            "parsed_uncertainty": round(p_u, 2),
        })

    return {
        "has_shoreline": True,
        "filename": s.shoreline_filename,
        "columns": cols,
        "date_col": date_col,
        "date_format": date_fmt,
        "uncertainty_col": unc_col,
        "default_uncertainty": s.default_uncertainty,
        "preview_rows": rows,
        "detected_years": unique_years,
    }


@app.get("/api/session/{sid}/params")
def get_params(sid: str):
    return _params(_require(sid))


@app.patch("/api/session/{sid}/params")
def patch_params(sid: str, patch: ParamPatch):
    s = _require(sid)
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    return _params(s)


@app.get("/api/session/{sid}/shoreline/fields")
def get_shoreline_fields(sid: str):
    s = _require(sid)
    return _build_shoreline_preview(s)


@app.post("/api/session/{sid}/shoreline/fields")
def set_shoreline_fields(sid: str, req: FieldMappingRequest):
    s = _require(sid)
    s.date_col = req.date_col
    s.date_format = req.date_format or "auto"
    s.default_uncertainty = max(0.1, float(req.default_uncertainty))

    # If user wants to create a new uncertainty column
    if req.create_uncertainty_col and s.shoreline_path and os.path.exists(s.shoreline_path):
        try:
            gdf = gpd.read_file(s.shoreline_path)
            new_col = req.create_uncertainty_col.strip()
            if new_col:
                gdf[new_col] = float(s.default_uncertainty)
                gdf.to_file(s.shoreline_path, driver="GeoJSON")
                s.uncertainty_col = new_col
                _log(s, f"Created uncertainty column '{new_col}' with default ±{s.default_uncertainty}m")
        except Exception as e:
            _log(s, f"Could not create uncertainty column: {e}", "WARNING")
    else:
        s.uncertainty_col = req.uncertainty_col if req.uncertainty_col else None

    _log(s, f"Field mapping updated: date='{s.date_col}' (format={s.date_format}), uncertainty='{s.uncertainty_col or 'Default ' + str(s.default_uncertainty) + 'm'}'")
    return _build_shoreline_preview(s)


@app.post("/api/session/{sid}/clear")
def clear_session(sid: str):
    s = _require(sid)
    s.shoreline_path = s.baseline_path = None
    s.shoreline_filename = s.baseline_filename = ""
    s.transects = None
    s.series_list = []
    s.results = {}
    _log(s, "Session cleared.")
    return _params(s)


# ── Uploads & data loading ──────────────────────────────────────────────────

async def _save_upload(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename or "layer.geojson")[1].lower() or ".geojson"
    if suffix in [".shp", ".dbf", ".shx", ".prj"]:
        raise HTTPException(
            status_code=400,
            detail="Shapefiles (.shp) are not supported. SHIFT standardises exclusively on standard GeoJSON (.geojson / .json) files."
        )
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(await file.read())
    tmp.close()
    return tmp.name


@app.post("/api/session/{sid}/upload/shoreline")
async def upload_shoreline(sid: str, file: UploadFile):
    s = _require(sid)
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
        _log(s, f"Shoreline loaded: {s.shoreline_filename} ({len(gdf)} features, CRS {gdf.crs})")
        return {
            "filename": s.shoreline_filename, "n_features": len(gdf), "columns": cols,
            "date_col": date_cand, "uncertainty_col": unc_cand,
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post("/api/session/{sid}/upload/baseline")
async def upload_baseline(sid: str, file: UploadFile):
    s = _require(sid)
    path = await _save_upload(file)
    try:
        gdf = gpd.read_file(path)
        s.baseline_path = path
        s.baseline_filename = file.filename or "baseline.geojson"
        _log(s, f"Baseline loaded: {s.baseline_filename} ({len(gdf)} features)")
        return {"filename": s.baseline_filename, "n_features": len(gdf)}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post("/api/session/{sid}/demo")
def load_demo(sid: str):
    s = _require(sid)
    
    custom_sl = r"D:\thesis-work\shore-geojson\bhola.geojson"
    custom_bl = r"D:\thesis-work\shore-geojson\baseline_1.geojson"
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_sl = os.path.join(root_dir, "sample_data", "bhola.geojson")
    bundled_bl = os.path.join(root_dir, "sample_data", "baseline_1.geojson")

    if os.path.exists(custom_sl) and os.path.exists(custom_bl):
        sl_path, bl_path = custom_sl, custom_bl
        sl_fname, bl_fname = "bhola.geojson", "baseline_1.geojson"
    elif os.path.exists(bundled_sl) and os.path.exists(bundled_bl):
        sl_path, bl_path = bundled_sl, bundled_bl
        sl_fname, bl_fname = "bhola.geojson", "baseline_1.geojson"
    else:
        out_dir = os.path.join(tempfile.gettempdir(), "shift_sample")
        sl_path = os.path.join(out_dir, "sample_shorelines.geojson")
        bl_path = os.path.join(out_dir, "sample_baseline.geojson")
        if not (os.path.exists(sl_path) and os.path.exists(bl_path)):
            sl_path, bl_path = pipeline.generate_sample_data(out_dir)
        sl_fname, bl_fname = "sample_shorelines.geojson", "sample_baseline.geojson"

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

    _log(s, f"Demo dataset loaded: {sl_fname} ({len(gdf_sl)} shorelines) and {bl_fname}.")
    return {
        "shoreline": {"filename": s.shoreline_filename, "n_features": len(gdf_sl), "columns": cols,
                      "date_col": date_cand, "uncertainty_col": unc_cand},
        "baseline": {"filename": s.baseline_filename, "n_features": len(gpd.read_file(bl_path))},
    }


@app.post("/api/session/{sid}/auto-baseline")
def auto_baseline(sid: str):
    s = _require(sid)
    if not s.shoreline_path:
        raise HTTPException(status_code=400, detail="Load shorelines first.")
    try:
        sl = gpd.read_file(s.shoreline_path)
        bl = pipeline.create_synthetic_baseline(sl, buffer_distance=s.buffer_distance)
        tmp = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False)
        tmp.close()  # close handle first — Windows won't let GeoPandas write to an open file
        bl.to_crs("EPSG:4326").to_file(tmp.name, driver="GeoJSON")
        s.baseline_path = tmp.name
        s.baseline_filename = "auto_baseline.geojson"
        _log(s, f"Auto-baseline constructed ({s.buffer_distance}m buffer).")
        return {"filename": s.baseline_filename, "n_features": len(bl)}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


# ── Layer / data reads ──────────────────────────────────────────────────────

@app.get("/api/session/{sid}/layers/shorelines")
def layer_shorelines(sid: str):
    return gj.shorelines_geojson(_require(sid))


@app.get("/api/session/{sid}/layers/baseline")
def layer_baseline(sid: str):
    return gj.baseline_geojson(_require(sid))


@app.get("/api/session/{sid}/layers/transects")
def layer_transects(sid: str):
    return gj.transects_geojson(_require(sid))


@app.get("/api/session/{sid}/layers/choropleth")
def layer_choropleth(sid: str):
    return gj.rate_choropleth(_require(sid))


@app.get("/api/session/{sid}/layers/forecast")
def layer_forecast(sid: str):
    return gj.forecast_geojson(_require(sid))


@app.get("/api/session/{sid}/table")
def get_table(sid: str):
    return {"rows": serialize.table_rows(_require(sid))}


@app.get("/api/session/{sid}/diagnostics")
def get_diagnostics(sid: str):
    return serialize.diagnostics(_require(sid)) or {"n_transects": 0, "rows": [], "rmse_improvement": 0}


@app.get("/api/session/{sid}/summary")
def get_summary(sid: str):
    return serialize.summary_stats(_require(sid)) or {}


@app.get("/api/session/{sid}/chart/{tid}")
def get_chart(sid: str, tid: int):
    data = serialize.chart_data(_require(sid), tid)
    if data is None:
        raise HTTPException(status_code=404, detail="Transect not found.")
    return data


@app.get("/api/session/{sid}/forecast-models")
def forecast_models(sid: str):
    s = _require(sid)
    r = s.results
    available = []
    if r.get("breakpoint"):
        available.append("Breakpoint (Post-break Rate)")
    if r.get("theilsen"):
        available.append("Theil-Sen Robust Rate")
    if r.get("ransac"):
        available.append("RANSAC Robust Rate")
    if r.get("classic"):
        available += ["Linear Regression (LRR)", "Classic Endpoint Rate (EPR)"]
    if r.get("rf"):
        available.append("Random Forest Benchmark")
    if r.get("bayesian"):
        available.append("Bayesian Changepoint")
    return {"models": available}


# ── WebSocket progress-streamed jobs ────────────────────────────────────────

async def _run_job(ws: WebSocket, s: Session, fn):
    """Run a blocking pipeline fn in a worker thread, streaming progress frames."""
    await ws.accept()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress(msg: str, prog: float):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "message": msg, "progress": prog})
        except Exception:
            pass

    async def worker():
        try:
            await asyncio.to_thread(fn, s, progress)
            await queue.put({"type": "done"})
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            _log(s, traceback.format_exc(), "ERROR")
            try:
                await queue.put({"type": "error", "message": str(ex)})
            except Exception:
                pass

    task = asyncio.create_task(worker())
    try:
        while True:
            frame = await queue.get()
            await ws.send_json(frame)
            if frame.get("type") in ("done", "error"):
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as ex:
        _log(s, f"WebSocket job error: {ex}", "ERROR")
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await ws.close()
        except Exception:
            pass


@app.websocket("/api/session/{sid}/ws/preview")
async def ws_preview(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.preview_transects)


@app.websocket("/api/session/{sid}/ws/analyze")
async def ws_analyze(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.run_analysis)


@app.websocket("/api/session/{sid}/ws/forecast")
async def ws_forecast(ws: WebSocket, sid: str):
    s = store.get(sid)
    if s is None:
        await ws.close(code=4404)
        return
    await _run_job(ws, s, pipeline.generate_forecast)


# ── Exports ─────────────────────────────────────────────────────────────────

def _build_full_rates_df(s: Session) -> pd.DataFrame:
    r = s.results or {}
    classic = r.get("classic", [])
    theilsen = r.get("theilsen", [])
    ransac = r.get("ransac", [])
    breakpt = r.get("breakpoint", [])
    rf = r.get("rf", [])

    rows = []
    for i, ser in enumerate(s.series_list):
        cl = classic[i] if i < len(classic) else None
        ts = theilsen[i] if i < len(theilsen) else None
        rs = ransac[i] if i < len(ransac) else None
        bp = breakpt[i] if i < len(breakpt) else None
        rfr = rf[i] if i < len(rf) else None

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
            "lrr_r2": round(cl.lrr_r2, 4) if cl and cl.lrr_r2 is not None else None,
            "wlr_m_yr": round(cl.wlr, 3) if cl and cl.wlr is not None else None,
            "wlr_r2": round(cl.wlr_r2, 4) if cl and cl.wlr_r2 is not None else None,
            "nsm_m": round(cl.nsm, 2) if cl and cl.nsm is not None else None,
            "sce_m": round(cl.sce, 2) if cl and cl.sce is not None else None,
            "theilsen_m_yr": round(ts.theilsen, 3) if ts and ts.theilsen is not None else None,
            "theilsen_r2": round(ts.theilsen_r2, 4) if ts and ts.theilsen_r2 is not None else None,
            "ransac_m_yr": round(rs.ransac, 3) if rs and rs.ransac is not None else None,
            "ransac_r2": round(rs.ransac_r2, 4) if rs and rs.ransac_r2 is not None else None,
            "breakpoint_rate_m_yr": round(bp.overall_rate, 3) if bp and bp.overall_rate is not None else None,
            "break_year": round(bp.breakpoints[-1].year, 2) if bp and bp.breakpoints else None,
            "n_regimes": len(bp.breakpoints) + 1 if bp and bp.breakpoints else 1,
            "rf_rate_m_yr": round(rfr.overall_rate, 3) if rfr and rfr.overall_rate is not None else None,
            "rf_rmse_m": round(rfr.rf_rmse, 3) if rfr and rfr.rf_rmse is not None else None,
        })
    return pd.DataFrame(rows)


def _build_intersections_df(s: Session) -> pd.DataFrame:
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


def _build_readme(s: Session) -> str:
    n_tr = len(s.series_list)
    n_sl = len(s.series_list[0]) if s.series_list else 0
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
1. shift_transect_rates.csv
   Complete tabular rate metrics for every transect across all calculated models:
   - EPR (End Point Rate, m/yr)
   - LRR (Linear Regression Rate, m/yr) & R² goodness of fit
   - WLR (Weighted Linear Regression, m/yr) & R²
   - NSM (Net Shoreline Movement, meters)
   - SCE (Shoreline Change Envelope, meters)
   - TSR (Theil-Sen Robust Rate, m/yr) & R²
   - RANSAC (Random Sample Consensus Rate, m/yr) & R²
   - Breakpoint (Pelt Changepoint Regime Shift Rate, m/yr, break year, n_regimes)
   - Random Forest (ML non-linear rate benchmark & RMSE)

2. transects_rates_envelope.geojson
   Spatial LineStrings clipped to the active shoreline envelope [min_dist, max_dist]
   with all rate attributes attached for 1-click styling in QGIS / ArcGIS Pro.

3. transects_full.geojson
   Full-length orthogonal transect lines cast from baseline origin.

4. intersections_raw.csv
   Measurement series per shoreline survey per transect (dates, decimal years, distances).

5. baseline.geojson & shorelines.geojson
   Original spatial input layers normalized in WGS84 (EPSG:4326).

6. forecast_shoreline.geojson & forecast_uncertainty_cone.geojson (if generated)
   Extrapolated shoreline position and confidence ribbon for the selected forward horizon.

7. session_config.json
   Machine-readable run configuration, algorithm settings, and metadata.

CITATION:
--------------------------------------------------------------------------------
SHIFT: Geospatial Breakpoint & Automated Shoreline Change Analysis Workbench
Built with Python (GeoPandas, Shapely, Scikit-Learn, Ruptures) & Next.js / Leaflet.
================================================================================
"""


@app.get("/api/session/{sid}/export/csv")
def export_csv(sid: str):
    s = _require(sid)
    if not s.results:
        raise HTTPException(status_code=400, detail="No results to export.")
    df = _build_full_rates_df(s)
    csv = df.to_csv(index=False)
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shift_transect_rates.csv"}
    )


@app.get("/api/session/{sid}/export/intersections.csv")
def export_intersections(sid: str):
    s = _require(sid)
    if not s.series_list:
        raise HTTPException(status_code=400, detail="No shoreline intersections to export.")
    df = _build_intersections_df(s)
    csv = df.to_csv(index=False)
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shift_intersections_raw.csv"}
    )


@app.get("/api/session/{sid}/export/transects.geojson")
def export_transects(sid: str):
    s = _require(sid)
    if s.transects is None:
        raise HTTPException(status_code=400, detail="No transects to export.")
    gdf = s.transects.to_crs("EPSG:4326")
    return Response(
        content=gdf.to_json(),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=shift_transects_full.geojson"}
    )


@app.get("/api/session/{sid}/export/transects_rates.geojson")
def export_transects_rates(sid: str):
    s = _require(sid)
    if not s.results or s.transects is None:
        raise HTTPException(status_code=400, detail="No analysis results to export.")
    ch = gj.rate_choropleth(s)
    geojson_dict = ch.get("geojson", {"type": "FeatureCollection", "features": []})
    return Response(
        content=json.dumps(geojson_dict),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=shift_transects_rates_envelope.geojson"}
    )


@app.get("/api/session/{sid}/export/forecast.geojson")
def export_forecast(sid: str):
    s = _require(sid)
    fc = gj.forecast_geojson(s)
    if not fc.get("line"):
        raise HTTPException(status_code=400, detail="No forecast generated.")
    return Response(
        content=json.dumps(fc["line"]),
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=shift_forecast_shoreline.geojson"}
    )


@app.get("/api/session/{sid}/export/bundle.zip")
def export_bundle(sid: str):
    s = _require(sid)
    if not s.results and s.transects is None and not s.shoreline_path:
        raise HTTPException(status_code=400, detail="No session data to export.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. README
        z.writestr("README.txt", _build_readme(s))

        # 2. Config JSON
        config_data = _params(s)
        z.writestr("session_config.json", json.dumps(config_data, indent=2))

        # 3. Rates CSV
        if s.results:
            rates_df = _build_full_rates_df(s)
            z.writestr("shift_transect_rates.csv", rates_df.to_csv(index=False))

        # 4. Intersections Raw CSV
        if s.series_list:
            intersections_df = _build_intersections_df(s)
            z.writestr("intersections_raw.csv", intersections_df.to_csv(index=False))

        # 5. Transects Rates Envelope GeoJSON
        if s.results and s.transects is not None:
            ch = gj.rate_choropleth(s)
            z.writestr("transects_rates_envelope.geojson", json.dumps(ch.get("geojson", {}), indent=2))

        # 6. Transects Full GeoJSON
        if s.transects is not None:
            z.writestr("transects_full.geojson", s.transects.to_crs("EPSG:4326").to_json())

        # 7. Baseline GeoJSON
        if s.baseline_path and os.path.exists(s.baseline_path):
            try:
                gdf_bl = gpd.read_file(s.baseline_path).to_crs("EPSG:4326")
                z.writestr("baseline.geojson", gdf_bl.to_json())
            except Exception:
                pass

        # 8. Shorelines GeoJSON
        if s.shoreline_path and os.path.exists(s.shoreline_path):
            try:
                gdf_sl = gpd.read_file(s.shoreline_path).to_crs("EPSG:4326")
                z.writestr("shorelines.geojson", gdf_sl.to_json())
            except Exception:
                pass

        # 9. Forecast Layers (if generated)
        if s.results and s.results.get("forecast"):
            fc = gj.forecast_geojson(s)
            if fc.get("line"):
                z.writestr("forecast_shoreline.geojson", json.dumps(fc["line"], indent=2))
            if fc.get("ribbon"):
                z.writestr("forecast_uncertainty_cone.geojson", json.dumps(fc["ribbon"], indent=2))

    buf.seek(0)
    now_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=shift_gis_bundle_{now_tag}.zip"}
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
