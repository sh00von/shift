"""Assemble per-transect (date, distance, uncertainty) series."""
from __future__ import annotations

import geopandas as gpd

from shift.models import TransectSeries


def build_series(intersections: gpd.GeoDataFrame) -> list[TransectSeries]:
    """
    Convert intersection table into one TransectSeries per transect.

    Parameters
    ----------
    intersections  Output of geometry.intersect_shorelines()

    Returns
    -------
    List of TransectSeries, sorted by transect_id, dates ascending.
    """
    series_list = []
    for tid, group in intersections.groupby("transect_id"):
        group = group.sort_values("date")
        # A rate needs at least two shoreline positions; DSAS only reports rates
        # for transects that intersect ≥2 shorelines. Skip the rest (e.g. transects
        # near the baseline ends that clip only one shoreline).
        if len(group) < 2:
            continue
        series_list.append(TransectSeries(
            transect_id=int(tid),
            dates=list(group["date"]),
            distances=list(group["distance"].astype(float)),
            uncertainties=list(group["uncertainty"].astype(float)),
        ))
    return series_list
