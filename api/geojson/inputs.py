"""GeoJSON builders for uploaded input layers: shorelines, baseline, transects."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
import shapely.geometry

from api.session import Session
from api.geojson._utils import SHORELINE_PALETTES, to_fc


def shorelines_geojson(state: Session) -> dict:
    if not state.shoreline_path:
        return {"type": "FeatureCollection", "features": []}

    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from api.pipeline import parse_dates

    gdf = gpd.read_file(state.shoreline_path).to_crs("EPSG:4326")
    date_col = state.date_col or next(
        (c for c in gdf.columns if any(k in c.lower() for k in ["date", "year", "time", "yr"])),
        None,
    )
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
    return to_fc(gdf, {"kind": "baseline"})


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
