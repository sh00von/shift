"""Synthetic data generators: demo baseline and sample shoreline data."""
from __future__ import annotations

import os

import geopandas as gpd
import numpy as np


def create_synthetic_baseline(
    shorelines: gpd.GeoDataFrame, buffer_distance: float
) -> gpd.GeoDataFrame:
    """Build an offset baseline by buffering the earliest shoreline seaward."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union

    sl = shorelines.copy()
    sl = sl[~sl.geometry.is_empty & sl.geometry.notna()]
    if len(sl) == 0:
        raise ValueError("Shoreline layer contains no valid geometries.")

    if sl.crs is None:
        sl = sl.set_crs("EPSG:4326")
    if sl.crs.is_geographic:
        try:
            sl = sl.to_crs(sl.estimate_utm_crs())
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
    return gpd.GeoDataFrame(
        {"name": ["auto_baseline"]},
        geometry=[LineString(list(longest.coords))],
        crs=sl.crs,
    )


def generate_sample_data(out_dir: str) -> tuple[str, str]:
    """Generate a synthetic multi-decadal eroding coastline + baseline (EPSG:4326)."""
    from shapely.geometry import LineString

    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(42)

    n_pts = 60
    lat = np.linspace(22.40, 22.62, n_pts)
    base_lon = 90.60 + 0.010 * np.sin(np.linspace(0, 3 * np.pi, n_pts))

    years = [1990, 1998, 2005, 2011, 2018, 2023]
    m_per_deg = 111_320 * np.cos(np.deg2rad(22.5))

    feats = []
    for yr in years:
        dt = yr - 1990
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
