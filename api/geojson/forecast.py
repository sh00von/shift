"""GeoJSON builder for forecast shoreline + uncertainty ribbon."""
from __future__ import annotations

import math

import geopandas as gpd
import shapely.geometry
from shapely.geometry import LineString, Point, Polygon

from api.session import Session
from api.geojson._utils import to_fc


def forecast_geojson(state: Session) -> dict:
    empty = {"line": None, "ribbon": None, "target_year": None, "ci_pct": None, "model": None}
    if not state.results or state.transects is None:
        return empty

    forecasts_by_model: dict = state.results.get("forecasts") or {}
    selected = state.forecast_model or (state.forecast_models[0] if state.forecast_models else None)
    if selected and selected in forecasts_by_model:
        fc_list = forecasts_by_model[selected]
    else:
        fc_list = state.results.get("forecast")
    if not fc_list:
        return empty

    gdf_tr = state.transects
    pts_fc, pts_lower, pts_upper = [], [], []
    target_year = None
    fc_map = {s.transect_id: fc for s, fc in zip(state.series_list, fc_list) if fc is not None}

    for _, row in gdf_tr.iterrows():
        tid = int(row["transect_id"])
        fc = fc_map.get(tid)
        if fc is None or not fc.forecast_years:
            continue
        target_year = int(fc.forecast_years[-1])
        coords = list(row["geometry"].coords)
        if len(coords) >= 2:
            x0, y0 = coords[0]
            x1, y1 = coords[-1]
            L = math.hypot(x1 - x0, y1 - y0)
            if L <= 0:
                continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            pts_fc.append(Point(x0 + ux * fc.forecast_distances[-1], y0 + uy * fc.forecast_distances[-1]))
            pts_lower.append(Point(x0 + ux * fc.forecast_lower[-1], y0 + uy * fc.forecast_lower[-1]))
            pts_upper.append(Point(x0 + ux * fc.forecast_upper[-1], y0 + uy * fc.forecast_upper[-1]))

    if len(pts_fc) < 2:
        return empty

    line = gpd.GeoDataFrame({"name": ["forecast"]}, geometry=[LineString(pts_fc)], crs=gdf_tr.crs).to_crs("EPSG:4326")
    ribbon_fc = None
    poly_coords = [p.coords[0] for p in pts_lower] + [p.coords[0] for p in pts_upper[::-1]]
    if len(poly_coords) >= 4:
        try:
            poly = gpd.GeoDataFrame({"name": ["ci"]}, geometry=[Polygon(poly_coords)], crs=gdf_tr.crs).to_crs("EPSG:4326")
            ribbon_fc = to_fc(poly, {"kind": "ribbon"})
        except Exception:
            pass

    return {
        "line": to_fc(line, {"kind": "forecast"}),
        "ribbon": ribbon_fc,
        "target_year": target_year,
        "ci_pct": int(state.forecast_ci * 100),
        "model": selected or "Kalman Filter (DSAS)",
    }
