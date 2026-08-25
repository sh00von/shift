"""API pipeline subpackage — one module per pipeline stage."""
from api.pipeline.loaders import parse_dates, load_shorelines, load_baseline
from api.pipeline.analysis import preview_transects, run_analysis
from api.pipeline.forecast import generate_forecast
from api.pipeline.diagnostics import run_montecarlo, run_cbc, compute_spatial
from api.pipeline.aln2d import run_aln2d
from api.pipeline.synthetic import create_synthetic_baseline, generate_sample_data

__all__ = [
    "parse_dates",
    "load_shorelines",
    "load_baseline",
    "preview_transects",
    "run_analysis",
    "generate_forecast",
    "run_montecarlo",
    "run_cbc",
    "compute_spatial",
    "run_aln2d",
    "create_synthetic_baseline",
    "generate_sample_data",
]
