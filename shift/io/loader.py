"""Load shorelines and baseline from any OGR-readable format."""
from __future__ import annotations
from datetime import date
from pathlib import Path

import geopandas as gpd


def load_shorelines(
    path: str | Path,
    date_col: str = "date",
    uncertainty_col: str = "uncertainty",
    default_uncertainty: float = 10.0,
    target_crs: str | int | None = None,
) -> gpd.GeoDataFrame:
    """
    Load a shoreline layer from any OGR format.

    Returns a GeoDataFrame with normalised columns:
      - geometry  : LineString
      - date      : datetime.date
      - uncertainty: float (metres)
    """
    gdf = gpd.read_file(path)

    if date_col not in gdf.columns:
        raise ValueError(f"Shoreline layer missing '{date_col}' column. "
                         f"Available: {list(gdf.columns)}")

    gdf = gdf.rename(columns={date_col: "date"})
    gdf["date"] = gpd.pd.to_datetime(gdf["date"]).dt.date

    if uncertainty_col in gdf.columns:
        gdf = gdf.rename(columns={uncertainty_col: "uncertainty"})
    else:
        gdf["uncertainty"] = default_uncertainty

    gdf["uncertainty"] = gdf["uncertainty"].astype(float)

    if target_crs is not None:
        gdf = gdf.to_crs(target_crs)

    gdf = gdf.sort_values("date").reset_index(drop=True)
    return gdf[["date", "uncertainty", "geometry"]]


def load_baseline(
    path: str | Path,
    layer: str | None = None,
    target_crs: str | int | None = None,
) -> gpd.GeoDataFrame:
    """Load a baseline layer. Returns GeoDataFrame with geometry column."""
    gdf = gpd.read_file(path, layer=layer)
    if target_crs is not None:
        gdf = gdf.to_crs(target_crs)
    return gdf
