"""Data loading utilities: date parsing, shoreline/baseline GeoDataFrame loaders."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from api.session import Session


def parse_dates(series: pd.Series, date_format: str = "auto") -> pd.Series:
    """Robust date parser: auto-detection, custom formats, integer years, regex fallback."""
    s_clean = series.copy()
    if pd.api.types.is_numeric_dtype(s_clean):
        if (s_clean.dropna().between(1800, 2200)).all():
            return pd.to_datetime(
                s_clean.astype(int).astype(str) + "-01-01", errors="coerce"
            ).dt.date

    s_str = s_clean.astype(str).str.strip()

    if date_format and date_format.lower() != "auto":
        fmt = date_format.strip()
        if fmt.upper() in ["YYYY", "%Y"]:
            years = s_str.str.extract(r"(\d{4})")[0]
            return pd.to_datetime(years + "-01-01", errors="coerce").dt.date
        if fmt.upper() in ["DD/MM/YYYY", "%D/%M/%Y"]:
            fmt = "%d/%m/%Y"
        elif fmt.upper() in ["YYYY-MM-DD", "%Y-%M-%D"]:
            fmt = "%Y-%m-%d"
        elif fmt.upper() in ["MM/DD/YYYY", "%M/%D/%Y"]:
            fmt = "%m/%d/%Y"
        elif fmt.upper() in ["DD-MM-YYYY"]:
            fmt = "%d-%m-%Y"
        try:
            parsed = pd.to_datetime(s_str, format=fmt, errors="coerce")
            if parsed.notnull().any():
                return parsed.dt.date
        except Exception:
            pass

    try:
        dt = pd.to_datetime(s_str, dayfirst=True, errors="coerce")
        if dt.notnull().sum() >= len(s_str) * 0.5:
            return dt.dt.date
    except Exception:
        pass

    try:
        dt = pd.to_datetime(s_str, dayfirst=False, errors="coerce")
        if dt.notnull().sum() >= len(s_str) * 0.5:
            return dt.dt.date
    except Exception:
        pass

    years = s_str.str.extract(r"(\d{4})")[0]
    return pd.to_datetime(years + "-01-01", errors="coerce").dt.date


def load_shorelines(state: Session) -> gpd.GeoDataFrame:
    sl = gpd.read_file(state.shoreline_path)
    date_col = state.date_col or next(
        (c for c in sl.columns if any(k in c.lower() for k in ["date", "year", "time", "yr"])),
        sl.columns[0],
    )
    sl["date"] = parse_dates(sl[date_col], state.date_format)
    unc_col = state.uncertainty_col or ""
    if unc_col and unc_col in sl.columns:
        sl = sl.rename(columns={unc_col: "uncertainty"})
    elif "Uncertainty" in sl.columns:
        sl = sl.rename(columns={"Uncertainty": "uncertainty"})
    elif "uncertainty" not in sl.columns:
        sl["uncertainty"] = state.default_uncertainty
    if sl.crs is None:
        sl = sl.set_crs("EPSG:4326")
    if sl.crs.is_geographic:
        sl = sl.to_crs(sl.estimate_utm_crs())
    return sl


def load_baseline(state: Session, crs) -> gpd.GeoDataFrame:
    bl = gpd.read_file(state.baseline_path)
    bl = bl.explode(index_parts=False).reset_index(drop=True)
    if bl.crs is None:
        bl = bl.set_crs("EPSG:4326")
    if crs is not None and bl.crs != crs:
        bl = bl.to_crs(crs)
    return bl
