import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

from shift.aln2d.engine import ALN2DEngine, ensure_polygon, sanitize_gdf_for_export


def test_ensure_polygon():
    # Closed line
    line = LineString([(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)])
    poly = ensure_polygon(line)
    assert poly.geom_type == "Polygon"
    assert poly.area == 100.0

    # Open line
    open_line = LineString([(0, 0), (0, 10), (10, 10), (10, 0)])
    poly2 = ensure_polygon(open_line)
    assert poly2.geom_type == "Polygon"
    assert poly2.area == 100.0


def test_aln2d_engine_synthetic():
    # Build two multi-epoch shorelines in a metric UTM CRS (e.g. EPSG:32646)
    # T1: square at (0,0) to (1000, 1000)
    poly_t1 = Polygon([(0, 0), (0, 1000), (1000, 1000), (1000, 0), (0, 0)])
    # T2: square eroded at right, from (0,0) to (800, 1000)
    poly_t2 = Polygon([(0, 0), (0, 1000), (800, 1000), (800, 0), (0, 0)])

    gdf = gpd.GeoDataFrame(
        {
            "date": ["01/01/2000", "01/01/2010"],
            "uncertainty": [5.0, 5.0],
        },
        geometry=[poly_t1, poly_t2],
        crs="EPSG:32646",
    )

    engine = ALN2DEngine(
        reach_length_meters=500.0,
        reach_buffer_meters=500.0,
        search_mask_buffer_meters=2000.0,
        target_epsg=32646,
    )

    out = engine.run(gdf, date_col="date")

    assert "erosion_gdf" in out
    assert "accretion_gdf" in out
    assert "reach_gdf" in out
    assert "summary_df" in out

    # Erosion should be detected for 2000 -> 2010
    ero_gdf = out["erosion_gdf"]
    assert not ero_gdf.empty
    # Eroded area = (1000 - 800) * 1000 = 200,000 m2 = 0.2 km2
    ero_area = ero_gdf.geometry.area.sum() / 1e6
    assert pytest.approx(ero_area, abs=0.01) == 0.2

    # Reaches should have computed rates
    reach_gdf = out["reach_gdf"]
    assert len(reach_gdf) > 0
    assert "net_2d_m_yr" in reach_gdf.columns
    assert "ero_2d_m_yr" in reach_gdf.columns
    assert "acc_2d_m_yr" in reach_gdf.columns

    # Summary table
    sum_df = out["summary_df"]
    assert not sum_df.empty
    assert "Eroded_km2" in sum_df.columns
    assert "Net_Balance_km2_yr" in sum_df.columns



def test_sanitize_gdf_for_export():
    gdf = gpd.GeoDataFrame(
        {
            "raw_line": [LineString([(0, 0), (1, 1)])],
            "val": [123],
        },
        geometry=[Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])],
        crs="EPSG:32646",
    )
    clean = sanitize_gdf_for_export(gdf)
    assert "raw_line" not in clean.columns
    assert "val" in clean.columns
