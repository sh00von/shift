"""Shared FastAPI dependencies, request models, and helper utilities."""
from __future__ import annotations

import datetime

from fastapi import HTTPException
from pydantic import BaseModel

from api.session import Session, store


def require(sid: str) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found. Create a new session.")
    return s


def log(state: Session, msg: str, level: str = "INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    state.logs.append(f"[{ts}] [{level}] {msg}")


def params(s: Session) -> dict:
    return {
        "spacing": s.spacing, "smoothing": s.smoothing, "transect_length": s.transect_length,
        "cast_side": s.cast_side, "buffer_distance": s.buffer_distance,
        "default_uncertainty": s.default_uncertainty,
        "run_classic": s.run_classic, "run_ekf": s.run_ekf,
        "aln2d_reach_length": s.aln2d_reach_length, "aln2d_reach_buffer": s.aln2d_reach_buffer,
        "aln2d_search_mask_buffer": s.aln2d_search_mask_buffer,
        "has_forecast_eval": s.forecast_eval is not None,
        "forecast_models": s.forecast_models, "forecast_model": s.forecast_model,
        "forecast_horizon": s.forecast_horizon, "forecast_ci": s.forecast_ci,
        "style_metric": s.style_metric, "color_ramp": s.color_ramp,
        "shoreline_palette": s.shoreline_palette,
        "date_col": s.date_col, "date_format": s.date_format, "uncertainty_col": s.uncertainty_col,
        "shoreline_filename": s.shoreline_filename, "baseline_filename": s.baseline_filename,
        "has_shoreline": s.shoreline_path is not None, "has_baseline": s.baseline_path is not None,
        "has_results": bool(s.results), "has_aln2d_results": s.aln2d_summary is not None,
        "logs": s.logs[-100:],
    }


class ParamPatch(BaseModel):
    spacing: float | None = None
    smoothing: float | None = None
    transect_length: float | None = None
    cast_side: str | None = None
    buffer_distance: float | None = None
    default_uncertainty: float | None = None
    run_classic: bool | None = None
    run_ekf: bool | None = None
    aln2d_reach_length: float | None = None
    aln2d_reach_buffer: float | None = None
    aln2d_search_mask_buffer: float | None = None
    forecast_models: list | None = None
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
