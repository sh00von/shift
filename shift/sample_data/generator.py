"""Generate sample coastal datasets for instant testing and demonstration."""
from __future__ import annotations
import os
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString


def generate_sample_data(output_dir: str = "sample_data") -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)

    # Base coordinates in UTM Zone 46N (EPSG:32646) — coastal Bangladesh
    # Coastline length approx 25 km from North to South
    n_pts = 100
    ys = np.linspace(2420000, 2445000, n_pts)
    
    # Baseline seaward line approx 2000m offshore with smooth meander
    base_x = 550000 + 450 * np.sin(ys / 5000)
    baseline_line = LineString(np.column_stack([base_x, ys]))
    gdf_base = gpd.GeoDataFrame({"id": [1], "name": ["offshore_baseline"]}, geometry=[baseline_line], crs="EPSG:32646").to_crs("EPSG:4326")
    base_path = os.path.join(output_dir, "sample_baseline.geojson")
    gdf_base.to_file(base_path, driver="GeoJSON")

    # Generate 8 multi-temporal historical surveys (1989 to 2024)
    years = [1989, 1994, 1999, 2004, 2009, 2014, 2019, 2024]
    dates = [
        "1989-02-12", "1994-01-20", "1999-03-15", "2004-02-10",
        "2009-01-25", "2014-03-02", "2019-02-18", "2024-01-30"
    ]
    uncertainties = [12.0, 10.0, 9.0, 8.0, 7.0, 5.0, 4.0, 3.5]
    satellites = ["Landsat 5 TM", "Landsat 5 TM", "Landsat 7 ETM+", "Landsat 7 ETM+", "Landsat 7 ETM+", "Landsat 8 OLI", "Sentinel-2A", "Sentinel-2B"]

    lines = []
    prop_dates = []
    prop_uncs = []
    prop_sats = []

    for yr, dt_str, unc, sat in zip(years, dates, uncertainties, satellites):
        retreat = np.zeros(n_pts)
        for i, y in enumerate(ys):
            # Spatial erosion hotspot around central delta apex (y = 2432500)
            sector_weight = np.exp(-((y - 2432500) ** 2) / (7000 ** 2))
            
            # Regime shift around year 2009:
            # Pre-2009 rate: ~ -6.5 m/yr
            # Post-2009 rate: ~ -18.5 m/yr in hotspot
            if yr <= 2009:
                accumulated = (yr - 1989) * (5.5 + 3.0 * sector_weight)
            else:
                pre_accum = (2009 - 1989) * (5.5 + 3.0 * sector_weight)
                post_accum = (yr - 2009) * (8.0 + 12.5 * sector_weight)
                accumulated = pre_accum + post_accum

            # Add realistic wave/tidal geomorphic noise
            noise = np.random.normal(0, 4.5)
            retreat[i] = accumulated + noise

        # Occasional satellite tidal outlier spike on 1999 survey
        if yr == 1999:
            retreat += np.where((ys > 2430000) & (ys < 2436000), 28.0, 0.0)

        sl_x = base_x + 1200 + retreat
        sl_line = LineString(np.column_stack([sl_x, ys]))
        lines.append(sl_line)
        prop_dates.append(dt_str)
        prop_uncs.append(unc)
        prop_sats.append(sat)

    gdf_sl = gpd.GeoDataFrame({
        "date": prop_dates,
        "uncertainty": prop_uncs,
        "satellite": prop_sats,
    }, geometry=lines, crs="EPSG:32646").to_crs("EPSG:4326")

    sl_path = os.path.join(output_dir, "sample_shorelines.geojson")
    gdf_sl.to_file(sl_path, driver="GeoJSON")

    return sl_path, base_path


if __name__ == "__main__":
    s, b = generate_sample_data()
    print("Generated realistic 8-survey dataset:", s, b)
