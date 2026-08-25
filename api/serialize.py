"""Serialise pipeline results into JSON for the frontend: attribute table rows,
transect time-series chart data, cross-model diagnostics, and summary stats.
Ported from attribute_table.py, transect_chart.py, diagnostics_view.py, and the
summary panel."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as st

from api.session import Session


def _f(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)

def table_rows(state: Session) -> list[dict]:
    r = state.results
    classic = r.get("classic", [])
    ekf = r.get("ekf", [])

    rows = []
    for i, s in enumerate(state.series_list):
        cl = classic[i] if i < len(classic) else None
        ek = ekf[i] if i < len(ekf) else None

        if cl and cl.lrr_significant is True and cl.lrr is not None:
            trend = "Erosion" if cl.lrr < 0 else "Accretion"
        elif cl and cl.lrr_significant is False:
            trend = "Stable"
        else:
            trend = "—"
        if cl and cl.lrr_ci_low is not None and cl.lrr_ci_high is not None:
            lrr_ci = f"{cl.lrr_ci_low:.2f} to {cl.lrr_ci_high:.2f}"
        else:
            lrr_ci = "—"

        rows.append({
            "id": s.transect_id,
            "epr": _f(cl.epr if cl else None),
            "lrr": _f(cl.lrr if cl else None),
            "lrr_ci": lrr_ci,
            "trend": trend,
            "wlr": _f(cl.wlr if cl else None),
            "ekf": _f(ek.ekf if ek else None),
        })
    return rows


def chart_data(state: Session, tid: int) -> dict | None:
    """Time-series traces for one transect, consumed by the frontend Plotly chart."""
    smap = {s.transect_id: s for s in state.series_list}
    s = smap.get(tid)
    if s is None:
        return None

    yrs = s.years()
    d = list(s.distances)
    r = state.results
    traces: list[dict] = [{
        "name": "Observed Positions", "kind": "markers+lines",
        "x": yrs, "y": d, "color": "#0284c7",
    }]

    cl = {x.transect_id: x for x in r.get("classic", [])}.get(tid)
    if cl and cl.lrr is not None and not math.isnan(cl.lrr):
        traces.append({
            "name": f"LRR Linear ({cl.lrr:+.2f} m/yr)", "kind": "line", "dash": "dash",
            "x": yrs, "y": [cl.lrr * (y - yrs[0]) + d[0] for y in yrs], "color": "#64748b",
        })

    ek = {x.transect_id: x for x in r.get("ekf", [])}.get(tid)
    if ek and ek.ekf is not None and not math.isnan(ek.ekf) and ek.fitted_years:
        traces.append({
            "name": f"EKF (fitted curve)", "kind": "line", "dash": "solid",
            "x": ek.fitted_years, "y": ek.fitted_values, "color": "#10b981",
        })
        traces.append({
            "name": f"EKF rate ({ek.ekf:+.2f} m/yr)", "kind": "line", "dash": "dot",
            "x": yrs, "y": [ek.ekf * (y - yrs[0]) + d[0] for y in yrs], "color": "#10b981",
        })

    # Multi-model forecasts
    FORECAST_COLORS = ["#9333ea", "#f59e0b", "#10b981", "#ef4444", "#0891b2", "#64748b"]
    forecasts = []
    for fi, (model_name, fc_list) in enumerate(r.get("forecasts", {}).items()):
        fc = {x.transect_id: x for x in fc_list if x is not None}.get(tid)
        if fc and fc.forecast_years:
            forecasts.append({
                "model": model_name,
                "ci_pct": int(state.forecast_ci * 100),
                "years": list(fc.forecast_years),
                "distances": list(fc.forecast_distances),
                "lower": list(fc.forecast_lower),
                "upper": list(fc.forecast_upper),
                "color": FORECAST_COLORS[fi % len(FORECAST_COLORS)],
            })
    # Fallback to legacy single forecast
    forecast = forecasts[0] if forecasts else None

    summary = [f"Transect #{tid}"]
    if cl:
        summary.append(f"EPR: {cl.epr:+.2f} m/yr  |  LRR: {cl.lrr:+.2f} m/yr")
    if ek and ek.ekf is not None:
        summary.append(f"EKF: {ek.ekf:+.2f} m/yr")
    return {
        "transect_id": tid,
        "traces": traces,
        "forecast": forecast,
        "forecasts": forecasts,
        "summary": "   |   ".join(summary),
    }



def summary_stats(state: Session) -> dict | None:
    r = state.results
    classic = r.get("classic", [])
    if not classic:
        return None

    eprs = [x.epr for x in classic if x and x.epr is not None and not math.isnan(x.epr)]
    lrrs = [x.lrr for x in classic if x and x.lrr is not None and not math.isnan(x.lrr)]

    n_eroding = sum(1 for e in eprs if e < 0)
    pct = (n_eroding / len(eprs) * 100) if eprs else 0.0

    return {
        "total_transects": len(state.series_list),
        "eroding": f"{pct:.1f}% ({n_eroding} transects)",
        "mean_epr": f"{np.mean(eprs):+.2f} m/yr" if eprs else "—",
        "mean_lrr": f"{np.mean(lrrs):+.2f} m/yr" if lrrs else "—",
        "max_erosion": f"{min(lrrs):+.2f} m/yr" if lrrs else "—",
        "max_accretion": f"{max(lrrs):+.2f} m/yr" if lrrs else "—",
    }


def aln2d_summary_rows(state: Session) -> list[dict]:
    """Returns rows for the 2D Morphodynamic Budget Summary table."""
    if state.aln2d_summary is None or state.aln2d_summary.empty:
        return []
    df = state.aln2d_summary.copy()
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "from_epoch": str(row.get("From_Epoch", "")),
            "to_epoch": str(row.get("To_Epoch", "")),
            "span_years": _f(row.get("Span_Years")),
            "eroded_km2": _f(row.get("Eroded_km2"), 3),
            "accreted_km2": _f(row.get("Accreted_km2"), 3),
            "erosion_rate_km2_yr": _f(row.get("Erosion_Rate_km2_yr"), 3),
            "accretion_rate_km2_yr": _f(row.get("Accretion_Rate_km2_yr"), 3),
            "net_balance_km2_yr": _f(row.get("Net_Balance_km2_yr"), 3),
        })
    return rows


def aln2d_validation_rows(state: Session) -> list[dict]:
    """Returns rows for the Academic Thesis Statistical Validation Matrix."""
    if state.aln2d_validation is None or state.aln2d_validation.empty:
        return []
    df = state.aln2d_validation.copy()
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "metric_name": str(row.get("metric_name", "")),
            "vs_lrr": str(row.get("vs_lrr", "")),
            "vs_epr": str(row.get("vs_epr", "")),
            "vs_kf": str(row.get("vs_kf", "")),
        })
    return rows


def forecast_eval_view(state: Session) -> dict:
    """Hindcast evaluation results for each forecast model."""
    ev = state.forecast_eval
    if not ev:
        return {"available": False, "rows": [], "best_model": None}

    def fmt(v, unit=""):
        return f"{v:.2f}{unit}" if v is not None else "—"

    rows = []
    for model, stats in ev.items():
        rows.append({
            "model": model,
            "rmse": fmt(stats.get("rmse"), " m"),
            "mae": fmt(stats.get("mae"), " m"),
            "n": stats.get("n", 0),
            "rmse_raw": stats.get("rmse"),
        })

    rows.sort(key=lambda r: (r["rmse_raw"] is None, r["rmse_raw"] if r["rmse_raw"] is not None else 1e9))
    best = rows[0]["model"] if rows and rows[0]["rmse_raw"] is not None else None

    return {
        "available": True,
        "rows": [{k: v for k, v in r.items() if k != "rmse_raw"} for r in rows],
        "best_model": best,
        "n_transects": len(state.series_list),
    }


def aln2d_reach_rows(state: Session) -> list[dict]:
    """Returns rows for the Reach-level 2D-ALN vs 1D comparisons table."""
    if state.aln2d_reaches is None or state.aln2d_reaches.empty:
        return []
    df = state.aln2d_reaches.copy()
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "reach_id": int(row.get("reach_id", 0)),
            "length_m": _f(row.get("length_m"), 1),
            "net_2d_m_yr": _f(row.get("net_2d_m_yr"), 2),
            "ero_2d_m_yr": _f(row.get("ero_2d_m_yr"), 2),
            "acc_2d_m_yr": _f(row.get("acc_2d_m_yr"), 2),
            "dsas_lrr_m_yr": _f(row.get("dsas_lrr_m_yr"), 2),
            "dsas_epr_m_yr": _f(row.get("dsas_epr_m_yr"), 2),
            "dsas_kf_m_yr": _f(row.get("dsas_kf_m_yr"), 2),
        })
    return rows

