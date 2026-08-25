"""Build GeoJSON layers + choropleth styling for the map. Ported from the old
NiceGUI map_view.py, but returns plain JSON-serialisable dicts instead of
injecting Leaflet JavaScript."""
from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.geometry
from shapely.geometry import LineString, Point, Polygon

from api.session import Session

RAMPS = {
    "Red-Yellow-Green (DSAS)": ["#dc2626", "#f87171", "#fef08a", "#86efac", "#16a34a"],
    "Turbo (Rainbow)": ["#30123b", "#458cfd", "#18e0bd", "#8bff4b", "#ebd339", "#dc3b07", "#7a0403"],
    "Viridis": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    "Coolwarm": ["#2563eb", "#93c5fd", "#f8fafc", "#fca5a5", "#dc2626"],
    "Magma": ["#000004", "#51127c", "#b73779", "#fb8861", "#fcfdbf"],
}

# Safe matplotlib colormaps offered for date-coded shorelines.
SHORELINE_PALETTES = ["turbo", "viridis", "plasma", "magma", "cividis", "cool", "spring"]

RAMP_GRADIENTS = {
    "Red-Yellow-Green (DSAS)": "linear-gradient(to right, #dc2626, #fef08a, #16a34a)",
    "Turbo (Rainbow)": "linear-gradient(to right, #30123b, #458cfd, #18e0bd, #8bff4b, #ebd339, #dc3b07, #7a0403)",
    "Viridis": "linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)",
    "Coolwarm": "linear-gradient(to right, #2563eb, #93c5fd, #f8fafc, #fca5a5, #dc2626)",
    "Magma": "linear-gradient(to right, #000004, #51127c, #b73779, #fb8861, #fcfdbf)",
}


def _rate_colour(v, vmin, vmax, metric: str, ramp: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "#94a3b8"
    t = 0.5 if vmin == vmax else max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
    stops = ["#7c3aed", "#2563eb", "#16a34a"] if "year" in metric.lower() else RAMPS.get(ramp, RAMPS["Red-Yellow-Green (DSAS)"])

    def h2r(c):
        c = c.lstrip("#")
        return int(c[:2], 16), int(c[2:4], 16), int(c[4:], 16)

    seg = 1.0 / (len(stops) - 1)
    i = min(int(t / seg), len(stops) - 2)
    lt = (t - i * seg) / seg
    r1, g1, b1 = h2r(stops[i])
    r2, g2, b2 = h2r(stops[i + 1])
    return f"#{int(r1+(r2-r1)*lt):02x}{int(g1+(g2-g1)*lt):02x}{int(b1+(b2-b1)*lt):02x}"


def shorelines_geojson(state: Session) -> dict:
    """Date-coloured shoreline features using selected date column and date format."""
    if not state.shoreline_path:
        return {"type": "FeatureCollection", "features": []}

    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from api.pipeline import parse_dates

    gdf = gpd.read_file(state.shoreline_path).to_crs("EPSG:4326")
    date_col = state.date_col or next((c for c in gdf.columns if any(k in c.lower() for k in ["date", "year", "time", "yr"])), None)
    features = []
    palette = state.shoreline_palette if state.shoreline_palette in SHORELINE_PALETTES else "turbo"

    if date_col and date_col in gdf.columns:
        try:
            parsed_dates = parse_dates(gdf[date_col], state.date_format)
            gdf["_parsed_date"] = pd.to_datetime(parsed_dates, errors="coerce")
            valid = gdf["_parsed_date"].notnull()
            if valid.any():
                t_min = gdf.loc[valid, "_parsed_date"].min().timestamp()
                t_max = gdf.loc[valid, "_parsed_date"].max().timestamp()
                cmap = plt.get_cmap(palette)
                for _, row in gdf.iterrows():
                    dt = row.get("_parsed_date")
                    if pd.notnull(dt) and t_max > t_min:
                        frac = (dt.timestamp() - t_min) / (t_max - t_min)
                        color = mcolors.to_hex(cmap(frac))
                        date_str = dt.strftime("%Y-%m-%d") if dt.month != 1 or dt.day != 1 else f"{dt.year}"
                    elif pd.notnull(dt):
                        color = "#0284c7"
                        date_str = dt.strftime("%Y-%m-%d")
                    else:
                        color, date_str = "#0284c7", str(row.get(date_col, "Unknown"))
                    features.append({
                        "type": "Feature",
                        "geometry": shapely.geometry.mapping(row["geometry"]),
                        "properties": {"color": color, "date_str": date_str, "raw_date": str(row.get(date_col, ""))},
                    })
        except Exception:
            pass

    if not features:
        for _, row in gdf.iterrows():
            features.append({
                "type": "Feature",
                "geometry": shapely.geometry.mapping(row["geometry"]),
                "properties": {"color": "#0284c7", "date_str": "Shoreline", "raw_date": ""},
            })

    return {"type": "FeatureCollection", "features": features}


def baseline_geojson(state: Session) -> dict:
    if not state.baseline_path:
        return {"type": "FeatureCollection", "features": []}
    gdf = gpd.read_file(state.baseline_path).to_crs("EPSG:4326")
    return _to_fc(gdf, {"kind": "baseline"})


def transects_geojson(state: Session) -> dict:
    if state.transects is None:
        return {"type": "FeatureCollection", "features": []}
    gdf = state.transects.to_crs("EPSG:4326")
    feats = []
    for _, row in gdf.iterrows():
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {"transect_id": int(row["transect_id"])},
        })
    return {"type": "FeatureCollection", "features": feats}


def _extract_vals(state: Session):
    nan = float("nan")
    r, s, m = state.results, state.series_list, state.style_metric or "LRR (m/yr)"
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
    for key in ["classic", "ekf"]:
        if key in r and r[key]:
            return [getattr(x, "lrr", getattr(x, "ekf", nan)) if x else nan for x in r[key]]
    return None


def rate_choropleth(state: Session) -> dict:
    """Colour-coded transect features + legend info for the style metric,
    clipped to each transect's active shoreline envelope [min_dist, max_dist] with padding."""
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

    tid_map = {s.transect_id: v for s, v in zip(state.series_list, vals) if v is not None and not (isinstance(v, float) and math.isnan(v))}
    series_map = {s.transect_id: s for s in state.series_list if s.distances}

    clipped_geoms = []
    clipped_tids = []
    clipped_vals = []

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

        p_start = (x0 + ux * d_start, y0 + uy * d_start)
        p_end = (x0 + ux * d_end, y0 + uy * d_end)

        clipped_geoms.append(LineString([p_start, p_end]))
        clipped_tids.append(tid)
        clipped_vals.append(v)

    if not clipped_geoms:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    gdf_clipped = gpd.GeoDataFrame(
        {"transect_id": clipped_tids, "val": clipped_vals},
        geometry=clipped_geoms,
        crs=state.transects.crs
    ).to_crs("EPSG:4326")

    feats = []
    for _, row in gdf_clipped.iterrows():
        tid = int(row["transect_id"])
        v = float(row["val"])
        color = _rate_colour(v, vmin, vmax, state.style_metric or "LRR", state.color_ramp or "Red-Yellow-Green (DSAS)")
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {
                "transect_id": tid,
                "value": v,
                "label": f"{v:+.2f} m/yr",
                "color": color,
            },
        })

    legend = {
        "title": (state.style_metric or "LRR (m/yr)").upper(),
        "min": round(vmin, 2),
        "max": round(vmax, 2),
        "gradient": RAMP_GRADIENTS.get(state.color_ramp, RAMP_GRADIENTS["Red-Yellow-Green (DSAS)"]),
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}


def forecast_geojson(state: Session) -> dict:
    """Forecast shoreline line + uncertainty ribbon polygon."""
    empty = {"line": None, "ribbon": None, "target_year": None, "ci_pct": None, "model": None}
    if not state.results or state.transects is None:
        return empty
    # Use the user-selected model; fall back to first available.
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
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            if L <= 0:
                continue
            ux, uy = dx / L, dy / L
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
            ribbon_fc = _to_fc(poly, {"kind": "ribbon"})
        except Exception:
            pass

    return {
        "line": _to_fc(line, {"kind": "forecast"}),
        "ribbon": ribbon_fc,
        "target_year": target_year,
        "ci_pct": int(state.forecast_ci * 100),
        "model": selected or "Kalman Filter (DSAS)",
    }


def _to_fc(gdf: gpd.GeoDataFrame, extra_props: dict | None = None) -> dict:
    feats = []
    for _, row in gdf.iterrows():
        props = {}
        for k, v in row.items():
            if k == "geometry":
                continue
            if isinstance(v, (int, float, str, bool)) or v is None:
                props[k] = None if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v
            elif hasattr(v, "isoformat"):
                props[k] = v.isoformat()
            else:
                props[k] = str(v)
        if extra_props:
            props.update(extra_props)
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": feats}


def aln2d_erosion_geojson(state: Session) -> dict:
    """GeoJSON polygon features for multi-epoch erosion mass."""
    if state.aln2d_erosion is None or state.aln2d_erosion.empty:
        return {"type": "FeatureCollection", "features": []}

    gdf = state.aln2d_erosion.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")
    return _to_fc(gdf, {"layer_type": "aln2d_erosion", "fillColor": "#ef4444", "color": "#dc2626"})


def aln2d_accretion_geojson(state: Session) -> dict:
    """GeoJSON polygon features for multi-epoch accretion mass."""
    if state.aln2d_accretion is None or state.aln2d_accretion.empty:
        return {"type": "FeatureCollection", "features": []}

    gdf = state.aln2d_accretion.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")
    return _to_fc(gdf, {"layer_type": "aln2d_accretion", "fillColor": "#10b981", "color": "#059669"})


BEST_METHOD_COLORS = {
    "EPR": "#64748b",
    "LRR": "#2563eb",
    "WLR": "#0891b2",
    "EKF": "#7c3aed",
}
_NO_WINNER_COLOR = "#cbd5e1"



def best_method_geojson(state: Session) -> dict:
    """Transect lines coloured by the winning (recommended) method per transect."""
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
            "properties": {
                "transect_id": tid,
                "winner": winner or "None",
                "color": color,
            },
        })

    legend = {
        "title": "Best method (per transect)",
        "categories": [
            {"label": m, "color": BEST_METHOD_COLORS[m], "count": seen[m]}
            for m in BEST_METHOD_COLORS if m in seen
        ],
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}


def aln2d_change_geojson(state: Session) -> dict:
    """Combined erosion + accretion mass as one diverging choropleth.

    Erosion polygons carry a *negative* signed rate and accretion a *positive* one,
    coloured on a symmetric red→neutral→green ramp (like the rate choropleth) so the
    two mass layers read as a single morphodynamic change surface.
    """
    parts = []
    if state.aln2d_erosion is not None and not state.aln2d_erosion.empty:
        g = state.aln2d_erosion.copy()
        g["change_type"] = "Erosion"
        g["signed_rate_km2_yr"] = -pd.to_numeric(g.get("rate_km2_yr"), errors="coerce")
        parts.append(g)
    if state.aln2d_accretion is not None and not state.aln2d_accretion.empty:
        g = state.aln2d_accretion.copy()
        g["change_type"] = "Accretion"
        g["signed_rate_km2_yr"] = pd.to_numeric(g.get("rate_km2_yr"), errors="coerce")
        parts.append(g)

    if not parts:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")

    vals = [v for v in gdf["signed_rate_km2_yr"].tolist()
            if v is not None and not (isinstance(v, float) and math.isnan(v))]
    maxabs = max((abs(v) for v in vals), default=1.0) or 1.0
    vmin, vmax = -maxabs, maxabs

    feats = []
    for _, row in gdf.iterrows():
        v = row.get("signed_rate_km2_yr")
        color = _rate_colour(v, vmin, vmax, "rate", state.color_ramp)
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {
                "layer_type": "aln2d_change",
                "change_type": str(row.get("change_type", "")),
                "period": str(row.get("period", "")),
                "rate_km2_yr": float(row["rate_km2_yr"]) if pd.notna(row.get("rate_km2_yr")) else None,
                "signed_rate_km2_yr": float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else None,
                "color": color,
            },
        })

    legend = {
        "title": "2D-ALN Net Change (km²/yr)",
        "min": round(-maxabs, 3),
        "max": round(maxabs, 3),
        "gradient": RAMP_GRADIENTS.get(state.color_ramp, RAMP_GRADIENTS["Red-Yellow-Green (DSAS)"]),
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}


def aln2d_reaches_geojson(state: Session) -> dict:
    """GeoJSON reach segments with 2D-ALN rate choropleth & 1D benchmarks."""
    if state.aln2d_reaches is None or state.aln2d_reaches.empty:
        return {
            "geojson": {"type": "FeatureCollection", "features": []},
            "legend": None,
        }

    gdf = state.aln2d_reaches.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")

    rates = [r for r in gdf["net_2d_m_yr"].tolist() if r is not None and not (isinstance(r, float) and math.isnan(r))]
    if not rates:
        return {"geojson": _to_fc(gdf), "legend": None}

    vmin, vmax = min(rates), max(rates)
    if vmin == vmax:
        vmin, vmax = vmin - 1.0, vmax + 1.0

    feats = []
    for _, row in gdf.iterrows():
        v = row.get("net_2d_m_yr")
        color = _rate_colour(v, vmin, vmax, "net_2d_m_yr", state.color_ramp)
        props = {
            "reach_id": int(row["reach_id"]),
            "length_m": float(row["length_m"]),
            "net_2d_m_yr": float(row["net_2d_m_yr"]),
            "ero_2d_m_yr": float(row["ero_2d_m_yr"]),
            "acc_2d_m_yr": float(row["acc_2d_m_yr"]),
            "dsas_lrr_m_yr": float(row.get("dsas_lrr_m_yr", 0.0)),
            "dsas_epr_m_yr": float(row.get("dsas_epr_m_yr", 0.0)),
            "dsas_kf_m_yr": float(row.get("dsas_kf_m_yr", 0.0)),
            "color": color,
        }
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": props,
        })

    legend = {
        "title": "2D-ALN Rate (m/yr)",
        "min": round(float(vmin), 2),
        "max": round(float(vmax), 2),
        "gradient": RAMP_GRADIENTS.get(state.color_ramp, RAMP_GRADIENTS["Red-Yellow-Green (DSAS)"]),
    }

    return {
        "geojson": {"type": "FeatureCollection", "features": feats},
        "legend": legend,
    }

