"""2D Areal-to-Linear Normalization (ALN) pipeline step."""
from __future__ import annotations

import os
from typing import Callable

import geopandas as gpd

from shift.aln2d import ALN2DEngine

from api.session import Session

ProgressCB = Callable[[str, float], None]


def run_aln2d(state: Session, progress: ProgressCB):
    """Execute 2D-ALN morphodynamic analysis."""
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

    progress("2D-ALN: Analysis successfully completed.", 1.0)
    return out
