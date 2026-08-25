"""Shared colour ramps, gradient strings, and GeoJSON helpers."""
from __future__ import annotations

import math

import geopandas as gpd
import shapely.geometry

RAMPS = {
    "Red-Yellow-Green (DSAS)": ["#dc2626", "#f87171", "#fef08a", "#86efac", "#16a34a"],
    "Turbo (Rainbow)": ["#30123b", "#458cfd", "#18e0bd", "#8bff4b", "#ebd339", "#dc3b07", "#7a0403"],
    "Viridis": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    "Coolwarm": ["#2563eb", "#93c5fd", "#f8fafc", "#fca5a5", "#dc2626"],
    "Magma": ["#000004", "#51127c", "#b73779", "#fb8861", "#fcfdbf"],
}

RAMP_GRADIENTS = {
    "Red-Yellow-Green (DSAS)": "linear-gradient(to right, #dc2626, #fef08a, #16a34a)",
    "Turbo (Rainbow)": "linear-gradient(to right, #30123b, #458cfd, #18e0bd, #8bff4b, #ebd339, #dc3b07, #7a0403)",
    "Viridis": "linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)",
    "Coolwarm": "linear-gradient(to right, #2563eb, #93c5fd, #f8fafc, #fca5a5, #dc2626)",
    "Magma": "linear-gradient(to right, #000004, #51127c, #b73779, #fb8861, #fcfdbf)",
}

SHORELINE_PALETTES = ["turbo", "viridis", "plasma", "magma", "cividis", "cool", "spring"]


def rate_colour(v, vmin, vmax, metric: str, ramp: str) -> str:
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


def to_fc(gdf: gpd.GeoDataFrame, extra_props: dict | None = None) -> dict:
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
