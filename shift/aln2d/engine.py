"""2D Areal-to-Linear Normalization (2D-ALN) Engine.

Standalone Pure-2D Morphodynamic Model (Zero-Transects / Zero-Baselines).
Continuous 2D Boolean polygon set differencing and reach-normalized migration rates.
"""
from __future__ import annotations

import math
import os
from typing import Any, Callable

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import make_valid
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from shift.geometry import cast_transects, intersect_shorelines
from shift.timeseries import build_series

ProgressCallback = Callable[[str, float], None]


def _dsas_reach_benchmark(
    gdf: gpd.GeoDataFrame,
    ref_raw_shore: Any,
    reach_length: float,
    transect_length: float,
    metric_crs: Any,
) -> dict[int, tuple[float, float, float]]:
    """1D DSAS benchmark per reach — the classic transect method the 2D-ALN result is validated against.

    Casts DSAS-style transects off the reference shore, intersects them with every epoch's raw
    shoreline, fits EPR/LRR/WLR per transect, then aggregates transect rates into their parent
    reach by along-shore position. Returns ``{reach_id: (mean_epr, mean_lrr, mean_wlr)}``.
    """
    # Imported lazily to avoid a shift.stats package-init import cycle.
    from shift.stats.classic import DSASMethod

    shore_lines = gpd.GeoDataFrame(
        {
            "date": gdf["parsed_date"].dt.date,
            "uncertainty": 1.0,
            "geometry": gdf["raw_line"],
        },
        crs=metric_crs,
    )
    baseline_gdf = gpd.GeoDataFrame({"geometry": [ref_raw_shore]}, crs=metric_crs)
    spacing = max(50.0, reach_length / 5.0)

    acc: dict[int, list[tuple[float, float, float]]] = {}
    dsas = DSASMethod()
    # Cast both sides — shorelines may migrate landward or seaward of the reference line.
    for side_offset, cast_side in ((0, "right"), (1_000_000, "left")):
        transects = cast_transects(
            baseline_gdf,
            spacing=spacing,
            smoothing_distance=reach_length,
            transect_length=transect_length,
            cast_side=cast_side,
            shorelines=shore_lines,
        )
        if transects.empty:
            continue
        origins = {
            int(row.transect_id): Point(row.geometry.coords[0])
            for row in transects.itertuples()
        }
        inter = intersect_shorelines(transects, shore_lines)
        if inter.empty:
            continue
        for ser in build_series(inter):
            if len(ser) < 2:
                continue
            origin = origins.get(int(ser.transect_id))
            if origin is None:
                continue
            res = dsas.fit(ser)
            ridx = int(ref_raw_shore.project(origin) // reach_length) + 1
            acc.setdefault(ridx, []).append(
                (res.epr or 0.0, res.lrr or 0.0, res.wlr or 0.0)
            )

    out: dict[int, tuple[float, float, float]] = {}
    for ridx, vals in acc.items():
        arr = np.array(vals, dtype=float)
        out[ridx] = (
            float(np.mean(arr[:, 0])),
            float(np.mean(arr[:, 1])),
            float(np.mean(arr[:, 2])),
        )
    return out


def _validation_matrix(reach_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Statistical validation matrix comparing the 2D-ALN net rate against each 1D DSAS model."""
    cols = ["metric_name", "vs_lrr", "vs_epr", "vs_kf"]
    if reach_gdf.empty or "net_2d_m_yr" not in reach_gdf.columns:
        return pd.DataFrame(columns=cols)

    truth = reach_gdf["net_2d_m_yr"].to_numpy(dtype=float)
    models = {
        "vs_lrr": reach_gdf.get("dsas_lrr_m_yr"),
        "vs_epr": reach_gdf.get("dsas_epr_m_yr"),
        "vs_kf": reach_gdf.get("dsas_kf_m_yr"),
    }

    def _corr(a: np.ndarray, b: np.ndarray) -> float:
        if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    metric_rows = {
        "Mean 1D Rate (m/yr)": lambda o: f"{np.mean(o):.3f}",
        "Pearson Correlation (r)": lambda o: f"{_corr(truth, o):.3f}",
        "RMSE (m/yr)": lambda o: f"{np.sqrt(np.mean((truth - o) ** 2)):.3f}",
        "Mean Abs. Error (m/yr)": lambda o: f"{np.mean(np.abs(truth - o)):.3f}",
        "Mean Bias 2D-1D (m/yr)": lambda o: f"{np.mean(truth - o):.3f}",
    }

    rows = []
    for name, fn in metric_rows.items():
        row = {"metric_name": name}
        for key, series in models.items():
            if series is None:
                row[key] = "N/A"
            else:
                row[key] = fn(series.to_numpy(dtype=float))
        rows.append(row)
    # Reference row: the 2D-ALN mean rate the models are compared against.
    rows.insert(0, {"metric_name": "Mean 2D-ALN Rate (m/yr)",
                    "vs_lrr": f"{np.mean(truth):.3f}",
                    "vs_epr": f"{np.mean(truth):.3f}",
                    "vs_kf": f"{np.mean(truth):.3f}"})
    return pd.DataFrame(rows, columns=cols)


def ensure_polygon(geom: Any) -> Any:
    """Closes open LineStrings into solid polygons preserving full vertex curvature."""
    if geom is None or geom.is_empty:
        return geom
    if geom.geom_type in ["LineString", "MultiLineString"]:
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            if len(coords) < 3:
                return geom
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            return make_valid(Polygon(coords))
        else:
            polys = []
            for part in geom.geoms:
                coords = list(part.coords)
                if len(coords) >= 3:
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    polys.append(Polygon(coords))
            if polys:
                union_geom = (
                    gpd.GeoSeries(polys).union_all()
                    if hasattr(gpd.GeoSeries, "union_all")
                    else gpd.GeoSeries(polys).unary_union
                )
                return make_valid(union_geom)
            return geom
    elif geom.geom_type in ["Polygon", "MultiPolygon"]:
        return make_valid(geom)
    return geom


def _longest_line(geom: Any) -> Any:
    """Reduce any line/boundary geometry to a single open LineString (the longest part)."""
    from shapely.ops import linemerge

    if geom is None or geom.is_empty:
        return geom
    if geom.geom_type == "LineString":
        return geom
    if geom.geom_type == "MultiLineString":
        merged = linemerge(geom)
        if merged.geom_type == "LineString":
            return merged
        return max(merged.geoms, key=lambda p: p.length)
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return _longest_line(geom.boundary)
    return geom


def region_to_baseline(shore: Any, base: Any) -> Any:
    """Close an open shoreline against a shared baseline instead of onto itself.

    Builds the polygon enclosed between the shoreline and the baseline. Because
    *every* epoch is closed against the **same** baseline, the artificial back-edge
    is identical across epochs and cancels in the Boolean difference — eliminating
    the spurious wedge that self-closing (connecting a line's own endpoints with a
    straight chord) produces. Endpoints are matched so the two short connectors are
    the only synthetic edges.
    """
    s = _longest_line(shore)
    b = _longest_line(base)
    if s is None or b is None or s.is_empty or b.is_empty:
        return None
    sc = list(s.coords)
    bc = list(b.coords)
    if len(sc) < 2 or len(bc) < 2:
        return None
    # Orient the baseline so bc[0] joins the shore END and bc[-1] joins the shore START.
    d_fwd = Point(bc[0]).distance(Point(sc[-1])) + Point(bc[-1]).distance(Point(sc[0]))
    d_rev = Point(bc[-1]).distance(Point(sc[-1])) + Point(bc[0]).distance(Point(sc[0]))
    if d_rev < d_fwd:
        bc = bc[::-1]
    ring = sc + bc
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return make_valid(Polygon(ring))


def sanitize_for_folium(df_in: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Purges non-active geometry attributes and non-serializable columns for GeoJSON / Web Maps."""
    df_clean = df_in.copy()
    drop_cols = [c for c in df_clean.columns if c in ["raw_line", "geometry_backup", "_parsed_date"]]
    for col in df_clean.columns:
        if col != df_clean.geometry.name and isinstance(df_clean[col].dtype, object):
            first_val = df_clean[col].dropna().iloc[0] if not df_clean[col].dropna().empty else None
            if hasattr(first_val, "geom_type"):
                drop_cols.append(col)
    df_clean = df_clean.drop(columns=list(set(drop_cols)), errors="ignore")

    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].dt.strftime("%d-%b-%Y")

    return df_clean


sanitize_gdf_for_export = sanitize_for_folium



class ALN2DEngine:
    """
    Standalone Pure-2D Morphodynamic Model (Zero-Transects / Zero-Baselines).
    Quantifies coastal & riverbank erosion/accretion using continuous 2D Boolean polygon
    differencing and 2D Areal-to-Linear Normalization (2D-ALN).
    """

    def __init__(
        self,
        reach_length_meters: float = 1000.0,
        reach_buffer_meters: float = 1000.0,
        search_mask_buffer_meters: float = 5000.0,
        target_epsg: int | None = None,
    ):
        self.reach_length_meters = reach_length_meters
        self.reach_buffer_meters = reach_buffer_meters
        self.search_mask_buffer_meters = search_mask_buffer_meters
        self.target_epsg = target_epsg

    def run(
        self,
        shorelines: gpd.GeoDataFrame | str,
        baseline: gpd.GeoDataFrame | str | None = None,
        date_col: str | None = None,
        date_format: str = "auto",
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """
        Executes the Pure 2D-ALN workflow:
        1. Datetime ingestion & metric UTM CRS standardization.
        2. Topology closing & bank search buffer mask generation.
        3. 2D Boolean set differencing across consecutive epochs (Areal erosion & accretion).
        4. Reach-based 2D Areal-to-Linear Normalization (2D-ALN).
        5. Export GeoJSONs & summary DataFrames.
        """

        def _p(msg: str, frac: float):
            if progress:
                progress(msg, frac)

        # ----------------------------------------------------------------------
        # 1. FILE CONFIGURATION & METRIC CRS REPROJECTION
        # ----------------------------------------------------------------------
        _p("2D-ALN: Loading shoreline dataset & standardizing CRS…", 0.05)
        if isinstance(shorelines, str):
            gdf = gpd.read_file(shorelines)
        else:
            gdf = shorelines.copy()

        if gdf.empty:
            raise ValueError("Input shoreline GeoDataFrame is empty.")

        if self.target_epsg is not None:
            if gdf.crs is None or gdf.crs.to_epsg() != self.target_epsg:
                gdf = gdf.to_crs(epsg=self.target_epsg)
        else:
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            if gdf.crs.is_geographic:
                utm_crs = gdf.estimate_utm_crs()
                gdf = gdf.to_crs(utm_crs)

        metric_crs = gdf.crs

        # ----------------------------------------------------------------------
        # 2. DATE PARSING & CHRONOLOGICAL SORTING
        # ----------------------------------------------------------------------
        _p("2D-ALN: Parsing dates and ordering chronological epochs…", 0.15)
        if date_col is None:
            date_col = next(
                (c for c in gdf.columns if any(k in c.lower() for k in ["date", "year", "time", "yr"])),
                gdf.columns[0],
            )

        s_str = gdf[date_col].astype(str).str.strip()
        if date_format and date_format.lower() != "auto":
            fmt = date_format.strip()
            if fmt.upper() in ["DD/MM/YYYY", "%D/%M/%Y"]:
                fmt = "%d/%m/%Y"
            elif fmt.upper() in ["YYYY-MM-DD"]:
                fmt = "%Y-%m-%d"
            elif fmt.upper() in ["MM/DD/YYYY"]:
                fmt = "%m/%d/%Y"
            gdf["parsed_date"] = pd.to_datetime(s_str, format=fmt, errors="coerce")
        else:
            gdf["parsed_date"] = pd.to_datetime(s_str, dayfirst=True, errors="coerce")

        if gdf["parsed_date"].isna().any():
            gdf["parsed_date"] = gdf["parsed_date"].fillna(
                pd.to_datetime(s_str, dayfirst=False, errors="coerce")
            )
        if gdf["parsed_date"].isna().any():
            years = s_str.str.extract(r"(\d{4})")[0]
            gdf["parsed_date"] = gdf["parsed_date"].fillna(
                pd.to_datetime(years + "-01-01", errors="coerce")
            )

        gdf = gdf.sort_values(by="parsed_date").reset_index(drop=True)
        gdf["epoch_label"] = gdf["parsed_date"].dt.strftime("%d-%b-%Y")
        gdf["year_float"] = gdf["parsed_date"].dt.year + (
            gdf["parsed_date"].dt.dayofyear / 365.25
        )

        unique_epochs = list(gdf["epoch_label"].unique())
        if len(unique_epochs) < 2:
            raise ValueError(
                f"2D-ALN requires at least 2 chronological survey epochs, found {len(unique_epochs)}."
            )

        # Preserve raw unclosed polyline before polygon conversion
        gdf["raw_line"] = gdf["geometry"]

        # Load the baseline (common back-edge) once, reprojected to the metric CRS.
        base_line_geom = None
        if baseline is not None:
            bl_gdf = gpd.read_file(baseline) if isinstance(baseline, str) else baseline.copy()
            if bl_gdf is not None and not bl_gdf.empty:
                if bl_gdf.crs is None:
                    bl_gdf = bl_gdf.set_crs("EPSG:4326")
                if bl_gdf.crs != metric_crs:
                    bl_gdf = bl_gdf.to_crs(metric_crs)
                base_line_geom = (
                    bl_gdf.geometry.union_all()
                    if hasattr(bl_gdf.geometry, "union_all")
                    else bl_gdf.geometry.unary_union
                )

        # ----------------------------------------------------------------------
        # 3. TOPOLOGY CLOSING & BANK SPATIAL MASKING
        # ----------------------------------------------------------------------
        _p("2D-ALN: Constructing bank-buffer mask and polygonizing shorelines…", 0.30)
        simplified = gdf["raw_line"].simplify(50.0)
        real_bank_union = (
            simplified.union_all()
            if hasattr(simplified, "union_all")
            else simplified.unary_union
        )
        bank_spatial_mask = real_bank_union.buffer(self.search_mask_buffer_meters)

        gdf["geometry"] = gdf["geometry"].apply(ensure_polygon)

        # ----------------------------------------------------------------------
        # 4. 2D BOOLEAN SET DIFFERENCING (AREAL EROSION & ACCRETION BUDGET)
        # ----------------------------------------------------------------------
        _p("2D-ALN: Computing 2D Boolean set differences across epochs…", 0.50)
        erosion_list, accretion_list, summary_stats = [], [], []

        for i in range(len(unique_epochs) - 1):
            ep1, ep2 = unique_epochs[i], unique_epochs[i + 1]
            t1_sub = gdf[gdf["epoch_label"] == ep1]
            t2_sub = gdf[gdf["epoch_label"] == ep2]

            dt_years = float(t2_sub["year_float"].iloc[0] - t1_sub["year_float"].iloc[0])
            if dt_years <= 0:
                dt_years = 1.0

            if base_line_geom is not None:
                # Close each epoch against the SHARED baseline → no self-closing chord,
                # so the synthetic back-edge cancels and no spurious wedge survives the
                # difference. The baseline marks the land side, so the region between the
                # shoreline and the baseline is "land"; erosion = land1 \ land2 (land lost).
                from shapely.ops import unary_union as _uu

                r1 = _uu([region_to_baseline(g, base_line_geom) for g in t1_sub["raw_line"] if g is not None])
                r2 = _uu([region_to_baseline(g, base_line_geom) for g in t2_sub["raw_line"] if g is not None])
                land1 = gpd.GeoDataFrame(geometry=[make_valid(r1)], crs=metric_crs)
                land2 = gpd.GeoDataFrame(geometry=[make_valid(r2)], crs=metric_crs)
            else:
                # Fallback (no baseline): self-closing polygons, as in the reference model.
                land1 = t1_sub[["geometry"]].dissolve()
                land2 = t2_sub[["geometry"]].dissolve()

            # Pure 2D Boolean differences clipped by bank search mask
            ero = gpd.overlay(land1, land2, how="difference").clip(bank_spatial_mask)
            acc = gpd.overlay(land2, land1, how="difference").clip(bank_spatial_mask)

            ero_area_km2 = float(ero.geometry.area.sum() / 1e6) if not ero.empty else 0.0
            acc_area_km2 = float(acc.geometry.area.sum() / 1e6) if not acc.empty else 0.0

            ero_rate_km2_yr = ero_area_km2 / dt_years
            acc_rate_km2_yr = acc_area_km2 / dt_years
            net_km2_yr = acc_rate_km2_yr - ero_rate_km2_yr

            if not ero.empty:
                ero["period"] = f"{ep1} to {ep2}"
                ero["rate_km2_yr"] = round(ero_rate_km2_yr, 4)
                erosion_list.append(ero)

            if not acc.empty:
                acc["period"] = f"{ep1} to {ep2}"
                acc["rate_km2_yr"] = round(acc_rate_km2_yr, 4)
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

        all_erosion = (
            gpd.GeoDataFrame(pd.concat(erosion_list, ignore_index=True), crs=metric_crs)
            if erosion_list
            else gpd.GeoDataFrame(columns=["period", "rate_km2_yr", "geometry"], crs=metric_crs)
        )
        all_accretion = (
            gpd.GeoDataFrame(pd.concat(accretion_list, ignore_index=True), crs=metric_crs)
            if accretion_list
            else gpd.GeoDataFrame(columns=["period", "rate_km2_yr", "geometry"], crs=metric_crs)
        )
        summary_df = pd.DataFrame(summary_stats)

        # ----------------------------------------------------------------------
        # 5. REACH-BASED 2D AREAL-TO-LINEAR NORMALIZATION (2D-ALN)
        # ----------------------------------------------------------------------
        _p("2D-ALN: Normalizing 2D surface areas into alongshore reach velocities…", 0.75)
        # 2D-ALN is a "zero-baseline" model: the reach reference is the EARLIEST
        # shoreline itself (its raw open polyline), so reaches hug the shore and
        # actually overlap the erosion/accretion polygons. An offshore transect
        # baseline must NOT be used here — it would place reaches far from the
        # shore and every reach clip would return zero. (Matches shift.py.)
        sub_raw = gdf[gdf["epoch_label"] == unique_epochs[0]]["raw_line"]
        ref_raw_shore = (
            sub_raw.union_all()
            if hasattr(sub_raw, "union_all")
            else sub_raw.unary_union
        )

        if hasattr(ref_raw_shore, "boundary") and ref_raw_shore.geom_type in ["Polygon", "MultiPolygon"]:
            ref_raw_shore = ref_raw_shore.boundary

        total_shore_length = float(ref_raw_shore.length)
        num_reaches = max(1, int(np.ceil(total_shore_length / self.reach_length_meters)))
        total_span_yrs = float(gdf["year_float"].max() - gdf["year_float"].min())
        if total_span_yrs <= 0:
            total_span_yrs = 1.0

        # 1D DSAS benchmark per reach — validates the 2D-ALN rates against the classic method.
        dsas_benchmark = _dsas_reach_benchmark(
            gdf,
            ref_raw_shore,
            self.reach_length_meters,
            transect_length=max(self.reach_buffer_meters * 2.0, self.search_mask_buffer_meters),
            metric_crs=metric_crs,
        )

        reach_records = []
        for i in range(num_reaches):
            start_d = i * self.reach_length_meters
            end_d = min((i + 1) * self.reach_length_meters, total_shore_length)

            pts = [ref_raw_shore.interpolate(d) for d in np.linspace(start_d, end_d, 25)]
            reach_line = LineString(pts)

            if reach_line.length == 0:
                continue

            reach_buffer = reach_line.buffer(self.reach_buffer_meters)
            clip_ero = all_erosion.clip(reach_buffer) if not all_erosion.empty else gpd.GeoDataFrame(geometry=[], crs=metric_crs)
            clip_acc = all_accretion.clip(reach_buffer) if not all_accretion.empty else gpd.GeoDataFrame(geometry=[], crs=metric_crs)

            ero_m2 = float(clip_ero.geometry.area.sum()) if not clip_ero.empty else 0.0
            acc_m2 = float(clip_acc.geometry.area.sum()) if not clip_acc.empty else 0.0

            # Areal-to-Linear Normalization equation: v = (Area / Length) / Time
            ero_m_yr = (ero_m2 / reach_line.length) / total_span_yrs
            acc_m_yr = (acc_m2 / reach_line.length) / total_span_yrs
            net_2d_m_yr = acc_m_yr - ero_m_yr

            epr, lrr, wlr = dsas_benchmark.get(i + 1, (0.0, 0.0, 0.0))
            reach_records.append({
                "reach_id": i + 1,
                "length_m": round(float(reach_line.length), 1),
                "net_2d_m_yr": round(net_2d_m_yr, 2),
                "ero_2d_m_yr": round(ero_m_yr, 2),
                "acc_2d_m_yr": round(acc_m_yr, 2),
                "dsas_epr_m_yr": round(epr, 2),
                "dsas_lrr_m_yr": round(lrr, 2),
                "dsas_kf_m_yr": round(wlr, 2),
                "geometry": reach_line,
            })

        reach_gdf = gpd.GeoDataFrame(reach_records, crs=metric_crs)
        validation_df = _validation_matrix(reach_gdf)

        _p("2D-ALN: Analysis complete.", 1.0)

        return {
            "erosion_gdf": all_erosion,
            "accretion_gdf": all_accretion,
            "reach_gdf": reach_gdf,
            "summary_df": summary_df,
            "validation_df": validation_df,
            "crs": metric_crs,
        }
