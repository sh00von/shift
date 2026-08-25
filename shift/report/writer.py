"""Write results to GeoPackage, summary .txt, and matplotlib figures."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from shift.models import RateResult, TransectSeries


def write_gpkg(
    results: list[RateResult],
    transects: gpd.GeoDataFrame,
    output_path: str | Path,
) -> None:
    """Join RateResult fields back onto transect geometries and write GeoPackage."""
    rows = []
    for r in results:
        row = {
            "transect_id": r.transect_id,
            "method": r.method,
            "sce": r.sce, "nsm": r.nsm, "epr": r.epr,
            "lrr": r.lrr,
            "wlr": r.wlr,
            "ekf": r.ekf,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    gdf = transects.merge(df, on="transect_id", how="left")
    gdf.to_file(str(output_path), driver="GPKG", layer="rates")


def write_summary_txt(
    results: list[RateResult],
    output_path: str | Path,
    method: str = "classic",
) -> None:
    """Write a DSAS-style summary text report."""
    rs = [r for r in results if r.method == method]
    n = len(rs)
    if n == 0:
        return

    lines = [
        f"SHIFT Summary Report",
        f"Method: {method}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total transects: {n}",
        "",
    ]

    lrr_rates = [r.lrr for r in rs if r.lrr is not None]
    if lrr_rates:
        lines += [
            f"LINEAR REGRESSION RATE (LRR, m/yr)",
            f"  Mean : {np.mean(lrr_rates):.2f}",
            f"  Max erosion : {min(lrr_rates):.2f}",
            f"  Max accretion: {max(lrr_rates):.2f}",
            f"  Erosional transects: {sum(1 for r in lrr_rates if r < 0)} "
            f"({100 * sum(1 for r in lrr_rates if r < 0) / n:.1f}%)",
            "",
        ]

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def plot_transect(
    series: TransectSeries,
    result: RateResult,
    output_path: str | Path | None = None,
) -> plt.Figure:
    """Plot distance-vs-time for one transect with fitted models and forecast."""
    years = series.years()
    d = series.distances

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.scatter(years, d, color="steelblue", zorder=5, label="Observed")
    ax.plot(years, d, color="steelblue", alpha=0.4)

    # LRR reference line
    if result.lrr is not None:
        y0 = years[0]
        lrr_line = [result.lrr * (y - y0) + d[0] for y in years]
        ax.plot(years, lrr_line, "k--", alpha=0.5, label=f"LRR {result.lrr:.1f} m/yr")

    # Forecast
    if result.forecast_years:
        fy = result.forecast_years
        fd = result.forecast_distances
        ax.plot(fy, fd, "r-", label="Forecast")
        ax.fill_between(fy, result.forecast_lower, result.forecast_upper,
                        color="red", alpha=0.15, label="90% CI")

    ax.set_xlabel("Year")
    ax.set_ylabel("Distance from baseline (m)")
    ax.set_title(f"Transect {series.transect_id} — {result.method}")
    ax.legend(fontsize=8)
    fig.tight_layout()

    if output_path:
        fig.savefig(str(output_path), dpi=150)
    return fig

