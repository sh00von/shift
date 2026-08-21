"""Perpendicular transect caster — follows the USGS DSAS method.

DSAS casts transects perpendicular to a reference baseline at a fixed alongshore
spacing. The transect *origin* stays on the actual baseline, but its orientation
is the baseline heading averaged over a "smoothing" window (±smoothing/2) so that
transects don't fan around small baseline irregularities. Each transect is cast to
one side of the baseline (DSAS "cast direction": left/right relative to the
digitized segment flow); the side that crosses the shorelines is what matters.
"""
from __future__ import annotations
import math

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, unary_union


def _merge_baseline(baseline: gpd.GeoDataFrame) -> LineString:
    """Merge baseline geometry into a single continuous LineString.

    Multipart baselines are merged; if they remain disjoint, the longest
    component is used (DSAS treats each baseline segment independently, but a
    single dominant line is the common case)."""
    merged = unary_union(baseline.geometry)
    if isinstance(merged, MultiLineString):
        merged = linemerge(merged)
    if isinstance(merged, MultiLineString):
        merged = max(merged.geoms, key=lambda g: g.length)
    return merged


def _smoothed_heading(line: LineString, dist: float, total: float, smoothing: float) -> float:
    """Baseline heading (radians, CCW from +x) at `dist`, averaged over the
    smoothing window. Uses the chord between the points ±smoothing/2 away — this
    is what gives DSAS its "straighter orthogonal reference" behaviour."""
    half = max(smoothing / 2.0, 1e-6)
    d0 = max(0.0, dist - half)
    d1 = min(total, dist + half)
    if d1 - d0 < 1e-9:
        d0, d1 = max(0.0, dist - 1.0), min(total, dist + 1.0)
    p0 = line.interpolate(d0)
    p1 = line.interpolate(d1)
    return math.atan2(p1.y - p0.y, p1.x - p0.x)


def _dominant_side(
    line: LineString,
    total: float,
    smoothing: float,
    transect_length: float,
    shorelines_union,
) -> int:
    """Return +1 (left of baseline flow) or -1 (right) — whichever side's
    transects intersect the shorelines more often. Mirrors the DSAS
    baseline-location / cast-direction flag, auto-detected from the data."""
    if shorelines_union is None or shorelines_union.is_empty:
        return 1
    left = right = 0
    n_probe = 25
    for k in range(n_probe):
        d = total * (k + 0.5) / n_probe
        origin = line.interpolate(d)
        heading = _smoothed_heading(line, d, total, smoothing)
        for sign, counter in ((+1, "L"), (-1, "R")):
            ang = heading + sign * math.pi / 2.0
            end = (origin.x + transect_length * math.cos(ang),
                   origin.y + transect_length * math.sin(ang))
            if LineString([(origin.x, origin.y), end]).intersects(shorelines_union):
                if sign == 1:
                    left += 1
                else:
                    right += 1
    return 1 if left >= right else -1


def _azimuth_deg(angle_rad: float) -> float:
    """Convert a math angle (CCW from +x) to a compass azimuth (deg CW from North)."""
    return (90.0 - math.degrees(angle_rad)) % 360.0


def cast_transects(
    baseline: gpd.GeoDataFrame,
    spacing: float = 250.0,
    smoothing_distance: float = 4000.0,
    transect_length: float = 10000.0,
    cast_side: str = "left",   # "left" | "right"
    shorelines: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame:
    """
    Cast transects perpendicular to the baseline at `spacing` intervals, DSAS-style.

    Parameters
    ----------
    baseline            GeoDataFrame with baseline geometry
    spacing             Alongshore spacing between transects (metres)
    smoothing_distance  Window over which the perpendicular heading is averaged (metres)
    transect_length     Length of each transect from the baseline origin (metres)
    cast_side           "left" or "right" of the baseline segment flow
    shorelines          Optional shorelines

    Returns
    -------
    GeoDataFrame with columns: transect_id, azimuth (deg from N), geometry (LineString).
    The first geometry vertex is always the baseline origin.
    """
    line = _merge_baseline(baseline)
    total = line.length
    if total <= 0:
        return gpd.GeoDataFrame({"transect_id": [], "azimuth": [], "geometry": []}, crs=baseline.crs)

    norm_side = str(cast_side).lower().strip() if cast_side else "left"
    side = 1 if norm_side in ("right", "r", "right of baseline", "seaward") else -1

    records = []
    n_transects = int(total // spacing)
    for i in range(n_transects + 1):
        d = i * spacing
        if d > total:
            break
        origin = line.interpolate(d)
        heading = _smoothed_heading(line, d, total, smoothing_distance)
        ang = heading + side * math.pi / 2.0
        end = (origin.x + transect_length * math.cos(ang), origin.y + transect_length * math.sin(ang))
        # First vertex is always the baseline origin (downstream measures distance from it).
        geom = LineString([(origin.x, origin.y), end])
        records.append({"transect_id": i, "azimuth": round(_azimuth_deg(ang), 1), "geometry": geom})

    return gpd.GeoDataFrame(records, crs=baseline.crs)


def intersect_shorelines(
    transects: gpd.GeoDataFrame,
    shorelines: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    For each transect × shoreline pair, compute distance from transect origin.

    Returns GeoDataFrame with columns:
      transect_id, date, uncertainty, distance (m), geometry (Point)
    """
    records = []
    for _, t in transects.iterrows():
        t_line = t.geometry
        if len(t_line.coords) == 3:
            origin = Point(t_line.coords[1])
        else:
            origin = Point(t_line.coords[0])
        for _, s in shorelines.iterrows():
            intersection = t_line.intersection(s.geometry)
            if intersection.is_empty:
                continue
            if intersection.geom_type == "MultiPoint":
                pt = list(intersection.geoms)[0]
            elif intersection.geom_type == "Point":
                pt = intersection
            else:
                continue
            dist = origin.distance(pt)
            records.append({
                "transect_id": int(t["transect_id"]),
                "date": s["date"],
                "uncertainty": float(s["uncertainty"]),
                "distance": dist,
                "geometry": pt,
            })

    if not records:
        return gpd.GeoDataFrame(
            {"transect_id": [], "date": [], "uncertainty": [], "distance": [], "geometry": []},
            geometry="geometry",
            crs=transects.crs,
        )
    return gpd.GeoDataFrame(records, crs=transects.crs)
