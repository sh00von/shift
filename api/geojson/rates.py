"""GeoJSON builders for rate choropleth and best-method layers."""
from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import shapely.geometry
from shapely.geometry import LineString

from api.session import Session
from api.geojson._utils import RAMP_GRADIENTS, rate_colour

BEST_METHOD_COLORS = {
    "EPR": "#64748b",
    "LRR": "#2563eb",
    "WLR": "#0891b2",
    "EKF": "#7c3aed",
}
_NO_WINNER_COLOR = "#cbd5e1"


def _extract_vals(state: Session):
    nan = float("nan")
    r = state.results
    m = state.style_metric or "LRR (m/yr)"
    if "EPR" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.epr if x else nan for x in res_list]
    if "WLR" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.wlr if x else nan for x in res_list]
    if "NSM" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.nsm if x else nan for x in res_list]
    if "SCE" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.sce if x else nan for x in res_list]
    if "LRR" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.lrr if x else nan for x in res_list]
    if "EKF" in m:
        res_list = r.get("ekf") or []
        return [x.ekf if x else nan for x in res_list]
    if "Sen" in m:
        res_list = r.get("classic") or r.get("dsas") or []
        return [x.sens if x else nan for x in res_list]
    for key in ["classic", "ekf"]:
        if key in r and r[key]:
            return [getattr(x, "lrr", getattr(x, "ekf", nan)) if x else nan for x in r[key]]
    return None


def rate_choropleth(state: Session) -> dict:
    if not state.results or state.transects is None or not state.series_list:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    vals = _extract_vals(state)
    if not vals:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    valid = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if valid:
        vmin = float(np.percentile(valid, 2))
        vmax = float(np.percentile(valid, 98))
        if vmin == vmax:
            vmin -= 1.0
            vmax += 1.0
    else:
        vmin, vmax = -5.0, 5.0

    tid_map = {s.transect_id: v for s, v in zip(state.series_list, vals)
               if v is not None and not (isinstance(v, float) and math.isnan(v))}
    series_map = {s.transect_id: s for s in state.series_list if s.distances}

    clipped_geoms, clipped_tids, clipped_vals = [], [], []
    for _, row in state.transects.iterrows():
        try:
            tid = int(row["transect_id"])
        except Exception:
            continue
        v = tid_map.get(tid)
        s = series_map.get(tid)
        if v is None or s is None or len(s.distances) < 1:
            continue
        coords = list(row["geometry"].coords)
        if len(coords) < 2:
            continue
        x0, y0 = coords[0]
        x1, y1 = coords[-1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L <= 0:
            continue
        ux, uy = dx / L, dy / L
        d_min = float(min(s.distances))
        d_max = float(max(s.distances))
        pad = max(20.0, 0.05 * (d_max - d_min) if d_max > d_min else 20.0)
        d_start = max(0.0, d_min - pad)
        d_end = min(L, d_max + pad)
        if d_end <= d_start:
            d_end = min(L, d_start + 10.0)
        clipped_geoms.append(LineString([(x0 + ux * d_start, y0 + uy * d_start), (x0 + ux * d_end, y0 + uy * d_end)]))
        clipped_tids.append(tid)
        clipped_vals.append(v)

    if not clipped_geoms:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    gdf_clipped = gpd.GeoDataFrame(
        {"transect_id": clipped_tids, "val": clipped_vals},
        geometry=clipped_geoms,
        crs=state.transects.crs,
    ).to_crs("EPSG:4326")

    feats = []
    for _, row in gdf_clipped.iterrows():
        tid = int(row["transect_id"])
        v = float(row["val"])
        color = rate_colour(v, vmin, vmax, state.style_metric or "LRR", state.color_ramp or "Red-Yellow-Green (DSAS)")
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {"transect_id": tid, "value": v, "label": f"{v:+.2f} m/yr", "color": color},
        })

    legend = {
        "title": (state.style_metric or "LRR (m/yr)").upper(),
        "min": round(vmin, 2),
        "max": round(vmax, 2),
        "gradient": RAMP_GRADIENTS.get(state.color_ramp, RAMP_GRADIENTS["Red-Yellow-Green (DSAS)"]),
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}


def best_method_geojson(state: Session) -> dict:
    sc = state.scorecard
    if not sc or state.transects is None or state.transects.empty:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    winners = {int(p["transect_id"]): p.get("winner") for p in sc.get("per_transect", [])}
    gdf = state.transects.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")

    feats = []
    seen: dict[str, int] = {}
    for _, row in gdf.iterrows():
        tid = int(row.get("transect_id", -1))
        winner = winners.get(tid)
        color = BEST_METHOD_COLORS.get(winner, _NO_WINNER_COLOR)
        if winner:
            seen[winner] = seen.get(winner, 0) + 1
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {"transect_id": tid, "winner": winner or "None", "color": color},
        })

    legend = {
        "title": "Best method (per transect)",
        "categories": [
            {"label": m, "color": BEST_METHOD_COLORS[m], "count": seen[m]}
            for m in BEST_METHOD_COLORS if m in seen
        ],
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}
