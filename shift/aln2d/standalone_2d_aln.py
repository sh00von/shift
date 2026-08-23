# ==============================================================================
# 2D AREAL-TO-LINEAR NORMALIZATION (2D-ALN) SHORELINE ENGINE
# Standalone Pure-2D Morphodynamic Model (Zero-Transects / Zero-Baselines)
# Target CRS: EPSG:32646 (UTM Zone 46N - Metric)
# ==============================================================================

import os
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import make_valid
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

# ------------------------------------------------------------------------------
# 1. FILE CONFIGURATION & GLOBAL PARAMETERS
# ------------------------------------------------------------------------------
GEOJSON_FILENAME = "sample_data/demo_shorelines.geojson"  # Path to multi-temporal GeoJSON
DATE_COLUMN_NAME = "date"                                # Date column (dd/mm/yyyy)
TARGET_EPSG = 32646                                      # Metric UTM projection
REACH_LENGTH_METERS = 1000                               # Alongshore reach segment length (1 km)

if not os.path.exists(GEOJSON_FILENAME):
    raise FileNotFoundError(
        f"[ERROR] '{GEOJSON_FILENAME}' not found. Please check the path."
    )

print(f"[INFO] Loading GeoJSON dataset: '{GEOJSON_FILENAME}'...")
gdf = gpd.read_file(GEOJSON_FILENAME)

if gdf.crs is None or gdf.crs.to_epsg() != TARGET_EPSG:
    print(f"[INFO] Reprojecting to EPSG:{TARGET_EPSG} (Meters)...")
    gdf = gdf.to_crs(epsg=TARGET_EPSG)

# ------------------------------------------------------------------------------
# 2. DATE PARSING & CHRONOLOGICAL SORTING
# ------------------------------------------------------------------------------
print(f"[INFO] Parsing dates from column: '{DATE_COLUMN_NAME}'...")
gdf["parsed_date"] = pd.to_datetime(
    gdf[DATE_COLUMN_NAME], format="%d/%m/%Y", errors="coerce"
)
if gdf["parsed_date"].isna().any():
    gdf["parsed_date"] = pd.to_datetime(gdf[DATE_COLUMN_NAME], dayfirst=True)

gdf = gdf.sort_values(by="parsed_date").reset_index(drop=True)
gdf["epoch_label"] = gdf["parsed_date"].dt.strftime("%d-%b-%Y")
gdf["year_float"] = gdf["parsed_date"].dt.year + (
    gdf["parsed_date"].dt.dayofyear / 365.25
)

unique_epochs = list(gdf["epoch_label"].unique())
print(f"[INFO] Found {len(unique_epochs)} chronological epochs.")

# Preserve raw open polyline before polygon conversion
gdf["raw_line"] = gdf["geometry"]

# ------------------------------------------------------------------------------
# 3. TOPOLOGY CLOSING & BANK SPATIAL MASKING
# ------------------------------------------------------------------------------
print("[INFO] Constructing bank-buffer mask and polygonizing shorelines...")

simplified = gdf["raw_line"].simplify(50.0)
real_bank_union = simplified.union_all() if hasattr(simplified, "union_all") else simplified.unary_union
bank_spatial_mask = real_bank_union.buffer(5000)  # 5 km search buffer


def ensure_polygon(geom):
    """Closes open LineStrings into solid polygons preserving full vertex curvature."""
    if geom.geom_type in ["LineString", "MultiLineString"]:
        coords = list(geom.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return make_valid(Polygon(coords))
    elif geom.geom_type in ["Polygon", "MultiPolygon"]:
        return make_valid(geom)
    return geom


gdf["geometry"] = gdf["geometry"].apply(ensure_polygon)

# ------------------------------------------------------------------------------
# 4. 2D BOOLEAN SET DIFFERENCING (AREAL EROSION & ACCRETION BUDGET)
# ------------------------------------------------------------------------------
print("[INFO] Computing 2D Boolean set differences across consecutive epochs...")

erosion_list, accretion_list, summary_stats = [], [], []

for i in range(len(unique_epochs) - 1):
    ep1, ep2 = unique_epochs[i], unique_epochs[i + 1]

    t1_sub = gdf[gdf["epoch_label"] == ep1]
    t2_sub = gdf[gdf["epoch_label"] == ep2]

    dt_years = t2_sub["year_float"].iloc[0] - t1_sub["year_float"].iloc[0]
    if dt_years <= 0:
        dt_years = 1.0

    land1 = t1_sub[["geometry"]].dissolve()
    land2 = t2_sub[["geometry"]].dissolve()

    # Pure 2D Boolean differences
    ero = gpd.overlay(land1, land2, how="difference").clip(bank_spatial_mask)
    acc = gpd.overlay(land2, land1, how="difference").clip(bank_spatial_mask)

    ero_area_km2 = ero.geometry.area.sum() / 1e6
    acc_area_km2 = acc.geometry.area.sum() / 1e6

    ero_rate_km2_yr = ero_area_km2 / dt_years
    acc_rate_km2_yr = acc_area_km2 / dt_years
    net_km2_yr = acc_rate_km2_yr - ero_rate_km2_yr

    ero["period"] = f"{ep1} to {ep2}"
    ero["rate_km2_yr"] = round(ero_rate_km2_yr, 4)

    acc["period"] = f"{ep1} to {ep2}"
    acc["rate_km2_yr"] = round(acc_rate_km2_yr, 4)

    erosion_list.append(ero)
    accretion_list.append(acc)

    summary_stats.append({
        "From_Epoch": ep1,
        "To_Epoch": ep2,
        "Span_Years": round(dt_years, 2),
        "Eroded_km2": round(ero_area_km2, 3),
        "Accreted_km2": round(acc_area_km2, 3),
        "Erosion_Rate_km2_yr": round(ero_rate_km2_yr, 3),
        "Accretion_Rate_km2_yr": round(acc_rate_km2_yr, 3),
        "Net_Balance_km2_yr": round(net_km2_yr, 3),
    })

all_erosion = gpd.GeoDataFrame(
    pd.concat(erosion_list, ignore_index=True), crs=TARGET_EPSG
)
all_accretion = gpd.GeoDataFrame(
    pd.concat(accretion_list, ignore_index=True), crs=TARGET_EPSG
)
summary_df = pd.DataFrame(summary_stats)

# ------------------------------------------------------------------------------
# 5. REACH-BASED 2D AREAL-TO-LINEAR NORMALIZATION (2D-ALN)
# ------------------------------------------------------------------------------
print(
    f"[INFO] Normalizing 2D surface areas into {REACH_LENGTH_METERS}m alongshore reach velocities..."
)

baseline_epoch = unique_epochs[0]
sub_raw = gdf[gdf["epoch_label"] == baseline_epoch]["raw_line"]
ref_raw_shore = sub_raw.union_all() if hasattr(sub_raw, "union_all") else sub_raw.unary_union

if hasattr(ref_raw_shore, "boundary") and ref_raw_shore.geom_type in ["Polygon", "MultiPolygon"]:
    ref_raw_shore = ref_raw_shore.boundary

total_shore_length = ref_raw_shore.length
num_reaches = int(np.ceil(total_shore_length / REACH_LENGTH_METERS))
total_span_yrs = gdf["year_float"].max() - gdf["year_float"].min()

reach_records = []
for i in range(num_reaches):
    start_d = i * REACH_LENGTH_METERS
    end_d = min((i + 1) * REACH_LENGTH_METERS, total_shore_length)

    pts = [ref_raw_shore.interpolate(d) for d in np.linspace(start_d, end_d, 25)]
    reach_line = LineString(pts)

    if reach_line.length == 0:
        continue

    reach_buffer = reach_line.buffer(REACH_LENGTH_METERS)
    clip_ero = all_erosion.clip(reach_buffer)
    clip_acc = all_accretion.clip(reach_buffer)

    ero_m2 = clip_ero.geometry.area.sum()
    acc_m2 = clip_acc.geometry.area.sum()

    # Areal-to-Linear Normalization equation: v = (Area / Length) / Time
    ero_m_yr = (ero_m2 / reach_line.length) / total_span_yrs
    acc_m_yr = (acc_m2 / reach_line.length) / total_span_yrs
    net_2d_m_yr = acc_m_yr - ero_m_yr

    reach_records.append({
        "reach_id": i + 1,
        "length_m": round(reach_line.length, 1),
        "net_2d_m_yr": round(net_2d_m_yr, 2),
        "ero_2d_m_yr": round(ero_m_yr, 2),
        "acc_2d_m_yr": round(acc_m_yr, 2),
        "geometry": reach_line,
    })

reach_gdf = gpd.GeoDataFrame(reach_records, crs=TARGET_EPSG)

# ------------------------------------------------------------------------------
# 6. EXPORT GEODATA & DISPLAY SUMMARY TABLES
# ------------------------------------------------------------------------------
all_erosion.to_file("processed_erosion_polygons.geojson", driver="GeoJSON")
all_accretion.to_file("processed_accretion_polygons.geojson", driver="GeoJSON")
reach_gdf.to_file("processed_linear_reach_rates.geojson", driver="GeoJSON")

print("\n" + "=" * 85)
print("             2D AREAL SHORELINE MORPHODYNAMIC BUDGET SUMMARY")
print("=" * 85)
print(summary_df.to_string(index=False))
print("=" * 85 + "\n")

print("=" * 85)
print("             REACH-BASED NORMALIZED MIGRATION RATES (FIRST 15 REACHES)")
print("=" * 85)
print(
    reach_gdf[[
        "reach_id",
        "length_m",
        "net_2d_m_yr",
        "ero_2d_m_yr",
        "acc_2d_m_yr",
    ]]
    .head(15)
    .to_string(index=False)
)
print("=" * 85 + "\n")


# ------------------------------------------------------------------------------
# 7. INTERACTIVE FOLIUM WEB MAP
# ------------------------------------------------------------------------------
def sanitize_for_folium(df_in):
    df_clean = df_in.copy()
    if "raw_line" in df_clean.columns:
        df_clean = df_clean.drop(columns=["raw_line"])
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].dt.strftime("%d-%b-%Y")
    return df_clean


earliest_layer = sanitize_for_folium(
    gdf[gdf["epoch_label"] == unique_epochs[0]]
).to_crs(epsg=4326)
latest_layer = sanitize_for_folium(
    gdf[gdf["epoch_label"] == unique_epochs[-1]]
).to_crs(epsg=4326)
ero_wgs = sanitize_for_folium(all_erosion).to_crs(epsg=4326)
acc_wgs = sanitize_for_folium(all_accretion).to_crs(epsg=4326)

center_lat = earliest_layer.geometry.centroid.y.mean()
center_lon = earliest_layer.geometry.centroid.x.mean()

m = folium.Map(
    location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron"
)

folium.GeoJson(
    earliest_layer,
    name=f"Baseline Shoreline ({unique_epochs[0]})",
    style_function=lambda x: {
        "color": "#2c3e50",
        "weight": 2,
        "dashArray": "5, 5",
    },
).add_to(m)

folium.GeoJson(
    latest_layer,
    name=f"Final Shoreline ({unique_epochs[-1]})",
    style_function=lambda x: {"color": "#2980b9", "weight": 2},
).add_to(m)

folium.GeoJson(
    ero_wgs,
    name="Erosion Surfaces (Land Loss)",
    style_function=lambda x: {
        "fillColor": "#e74c3c",
        "color": "#c0392b",
        "weight": 1,
        "fillOpacity": 0.65,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["period", "rate_km2_yr"],
        aliases=["Period:", "Erosion Rate (km²/yr):"],
    ),
).add_to(m)

folium.GeoJson(
    acc_wgs,
    name="Accretion Surfaces (Land Gain)",
    style_function=lambda x: {
        "fillColor": "#2ecc71",
        "color": "#27ae60",
        "weight": 1,
        "fillOpacity": 0.65,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["period", "rate_km2_yr"],
        aliases=["Period:", "Accretion Rate (km²/yr):"],
    ),
).add_to(m)

folium.LayerControl().add_to(m)
print(
    "[SUCCESS] 2D-ALN Engine complete. Generated GeoJSON exports."
)
