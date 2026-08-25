"""GeoJSON subpackage — one module per layer domain."""
from api.geojson._utils import RAMPS, RAMP_GRADIENTS, SHORELINE_PALETTES, rate_colour, to_fc
from api.geojson.inputs import shorelines_geojson, baseline_geojson, transects_geojson
from api.geojson.rates import rate_choropleth, best_method_geojson
from api.geojson.forecast import forecast_geojson
from api.geojson.aln2d import aln2d_erosion_geojson, aln2d_accretion_geojson, aln2d_change_geojson, aln2d_reaches_geojson
from api.geojson.diagnostics import cbc_geojson

__all__ = [
    "RAMPS",
    "RAMP_GRADIENTS",
    "SHORELINE_PALETTES",
    "rate_colour",
    "to_fc",
    "shorelines_geojson",
    "baseline_geojson",
    "transects_geojson",
    "rate_choropleth",
    "best_method_geojson",
    "forecast_geojson",
    "aln2d_erosion_geojson",
    "aln2d_accretion_geojson",
    "aln2d_change_geojson",
    "aln2d_reaches_geojson",
    "cbc_geojson",
]
