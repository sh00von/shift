"""Layer data, table, chart, summary, diagnostics, and forecast endpoints."""
from __future__ import annotations

import math

from fastapi import APIRouter, HTTPException

from api import geojson as gj
from api import pipeline, serialize
from api.deps import require

router = APIRouter()


@router.get("/session/{sid}/layers/shorelines")
def layer_shorelines(sid: str):
    return gj.shorelines_geojson(require(sid))


@router.get("/session/{sid}/layers/baseline")
def layer_baseline(sid: str):
    return gj.baseline_geojson(require(sid))


@router.get("/session/{sid}/layers/transects")
def layer_transects(sid: str):
    return gj.transects_geojson(require(sid))


@router.get("/session/{sid}/layers/choropleth")
def layer_choropleth(sid: str):
    return gj.rate_choropleth(require(sid))


@router.get("/session/{sid}/layers/forecast")
def layer_forecast(sid: str):
    return gj.forecast_geojson(require(sid))


@router.get("/session/{sid}/layers/aln2d/erosion")
def layer_aln2d_erosion(sid: str):
    return gj.aln2d_erosion_geojson(require(sid))


@router.get("/session/{sid}/layers/aln2d/accretion")
def layer_aln2d_accretion(sid: str):
    return gj.aln2d_accretion_geojson(require(sid))


@router.get("/session/{sid}/layers/aln2d/reaches")
def layer_aln2d_reaches(sid: str):
    return gj.aln2d_reaches_geojson(require(sid))


@router.get("/session/{sid}/layers/aln2d/change")
def layer_aln2d_change(sid: str):
    return gj.aln2d_change_geojson(require(sid))


@router.get("/session/{sid}/layers/cbc")
def layer_cbc(sid: str):
    return gj.cbc_geojson(require(sid))


@router.get("/session/{sid}/table")
def get_table(sid: str):
    return {"rows": serialize.table_rows(require(sid))}


@router.get("/session/{sid}/summary")
def get_summary(sid: str):
    return serialize.summary_stats(require(sid)) or {}


@router.get("/session/{sid}/chart/{tid}")
def get_chart(sid: str, tid: int):
    data = serialize.chart_data(require(sid), tid)
    if data is None:
        raise HTTPException(status_code=404, detail="Transect not found.")
    return data


@router.get("/session/{sid}/rate-profile")
def get_rate_profile(sid: str):
    """Numeric rates per transect for the along-shore rate profile chart."""
    s = require(sid)
    r = s.results or {}
    classic = r.get("classic", [])
    ekf = r.get("ekf", [])

    def _n(v):
        return None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 3)

    points = []
    for i, ser in enumerate(s.series_list):
        cl = classic[i] if i < len(classic) else None
        ek = ekf[i] if i < len(ekf) else None
        points.append({
            "transect_id": int(ser.transect_id),
            "epr": _n(cl.epr if cl else None),
            "lrr": _n(cl.lrr if cl else None),
            "wlr": _n(cl.wlr if cl else None),
            "sens": _n(cl.sens if cl else None),
            "ekf": _n(ek.ekf if ek else None),
        })
    return {"points": points}


@router.get("/session/{sid}/aln2d/summary")
def get_aln2d_summary(sid: str):
    return {"rows": serialize.aln2d_summary_rows(require(sid))}


@router.get("/session/{sid}/aln2d/validation")
def get_aln2d_validation(sid: str):
    return {"rows": serialize.aln2d_validation_rows(require(sid))}


@router.get("/session/{sid}/aln2d/reaches")
def get_aln2d_reaches(sid: str):
    return {"rows": serialize.aln2d_reach_rows(require(sid))}


@router.get("/session/{sid}/forecast/eval")
def get_forecast_eval(sid: str):
    return serialize.forecast_eval_view(require(sid))


@router.get("/session/{sid}/forecast-models")
def forecast_models_endpoint(sid: str):
    from shift.validation.forecast_eval import FORECAST_MODELS
    s = require(sid)
    available = FORECAST_MODELS if s.results else []
    return {"models": available, "selected": s.forecast_models}


@router.get("/session/{sid}/diagnostics")
def get_diagnostics(sid: str, window: int | None = None):
    return serialize.diagnostics_data(require(sid), window=window)


@router.post("/session/{sid}/diagnostics/cbc")
def run_cbc_endpoint(sid: str):
    s = require(sid)
    if not s.series_list:
        raise HTTPException(status_code=400, detail="Run analysis first.")
    results = pipeline.run_cbc(s, lambda m, p: None)
    return {"n": len(results)}
