"""Tests for pipeline helpers including synthetic baseline generation."""
import geopandas as gpd
from shapely.geometry import LineString
import pytest

from api.pipeline import create_synthetic_baseline, generate_sample_data


def test_create_synthetic_baseline():
    line1 = LineString([(90.0, 22.0), (90.0, 22.1)])
    line2 = LineString([(90.01, 22.0), (90.01, 22.1)])
    gdf = gpd.GeoDataFrame({"geometry": [line1, line2]}, crs="EPSG:4326")
    
    bl = create_synthetic_baseline(gdf, buffer_distance=500.0)
    assert isinstance(bl, gpd.GeoDataFrame)
    assert len(bl) == 1
    assert not bl.geometry.iloc[0].is_empty
