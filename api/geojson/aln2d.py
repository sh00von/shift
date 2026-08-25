"""GeoJSON builders for 2D-ALN polygon and reach layers."""
from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.geometry

from api.session import Session
from api.geojson._utils import RAMP_GRADIENTS, rate_colour, to_fc


def aln2d_erosion_geojson(state: Session) -> dict:
    if state.aln2d_erosion is None or state.aln2d_erosion.empty:
        return {"type": "FeatureCollection", "features": []}
    gdf = state.aln2d_erosion.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")
    return to_fc(gdf, {"layer_type": "aln2d_erosion", "fillColor": "#ef4444", "color": "#dc2626"})


def aln2d_accretion_geojson(state: Session) -> dict:
    if state.aln2d_accretion is None or state.aln2d_accretion.empty:
        return {"type": "FeatureCollection", "features": []}
    gdf = state.aln2d_accretion.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")
    return to_fc(gdf, {"layer_type": "aln2d_accretion", "fillColor": "#10b981", "color": "#059669"})


def aln2d_change_geojson(state: Session) -> dict:
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
        color = rate_colour(v, vmin, vmax, "rate", state.color_ramp)
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
    if state.aln2d_reaches is None or state.aln2d_reaches.empty:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    gdf = state.aln2d_reaches.copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32646")
    gdf = gdf.to_crs("EPSG:4326")

    rates = [r for r in gdf["net_2d_m_yr"].tolist()
             if r is not None and not (isinstance(r, float) and math.isnan(r))]
    if not rates:
        return {"geojson": to_fc(gdf), "legend": None}

    vmin, vmax = min(rates), max(rates)
    if vmin == vmax:
        vmin, vmax = vmin - 1.0, vmax + 1.0

    feats = []
    for _, row in gdf.iterrows():
        v = row.get("net_2d_m_yr")
        color = rate_colour(v, vmin, vmax, "net_2d_m_yr", state.color_ramp)
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {
                "reach_id": int(row["reach_id"]),
                "length_m": float(row["length_m"]),
                "net_2d_m_yr": float(row["net_2d_m_yr"]),
                "ero_2d_m_yr": float(row["ero_2d_m_yr"]),
                "acc_2d_m_yr": float(row["acc_2d_m_yr"]),
                "dsas_lrr_m_yr": float(row.get("dsas_lrr_m_yr", 0.0)),
                "dsas_epr_m_yr": float(row.get("dsas_epr_m_yr", 0.0)),
                "dsas_kf_m_yr": float(row.get("dsas_kf_m_yr", 0.0)),
                "color": color,
            },
        })

    legend = {
        "title": "2D-ALN Rate (m/yr)",
        "min": round(float(vmin), 2),
        "max": round(float(vmax), 2),
        "gradient": RAMP_GRADIENTS.get(state.color_ramp, RAMP_GRADIENTS["Red-Yellow-Green (DSAS)"]),
    }
    return {"geojson": {"type": "FeatureCollection", "features": feats}, "legend": legend}
