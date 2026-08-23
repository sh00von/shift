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
    theilsen = r.get("theilsen", [])
    ransac = r.get("ransac", [])
    breakpt = r.get("breakpoint", [])

    rows = []
    for i, s in enumerate(state.series_list):
        cl = classic[i] if i < len(classic) else None
        ts = theilsen[i] if i < len(theilsen) else None
        rs = ransac[i] if i < len(ransac) else None
        bp = breakpt[i] if i < len(breakpt) else None
        # Trend classification from the LRR 95% CI: a rate whose CI includes zero
        # is "Stable" (not statistically distinguishable from no change).
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
            "tsr": _f(ts.theilsen if ts else None),
            "ransac": _f(rs.ransac if rs else None),
            "wlr": _f(cl.wlr if cl else None),
            "bp_rate": _f(bp.overall_rate if bp else None),
            "bp_year": _f(bp.breakpoints[-1].year if bp and bp.breakpoints else None, 0),
            "n_brk": str(len(bp.breakpoints) + 1) if bp else "1",
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

    ts = {x.transect_id: x for x in r.get("theilsen", [])}.get(tid)
    if ts and ts.theilsen is not None and not math.isnan(ts.theilsen):
        traces.append({
            "name": f"Theil-Sen ({ts.theilsen:+.2f} m/yr)", "kind": "line", "dash": "dot",
            "x": yrs, "y": [ts.theilsen * (y - yrs[0]) + d[0] for y in yrs], "color": "#10b981",
        })

    rs = {x.transect_id: x for x in r.get("ransac", [])}.get(tid)
    if rs and rs.ransac is not None and not math.isnan(rs.ransac):
        traces.append({
            "name": f"RANSAC ({rs.ransac:+.2f} m/yr)", "kind": "line", "dash": "dashdot",
            "x": yrs, "y": [rs.ransac * (y - yrs[0]) + d[0] for y in yrs], "color": "#8b5cf6",
        })

    breaks = []
    bp = {x.transect_id: x for x in r.get("breakpoint", [])}.get(tid)
    if bp and bp.breakpoints:
        for b in bp.breakpoints:
            breaks.append({
                "year": b.year, "rate_before": b.rate_before, "rate_after": b.rate_after,
            })

    forecast = None
    fc = {x.transect_id: x for x in r.get("forecast", []) if x is not None}.get(tid)
    if fc and fc.forecast_years:
        forecast = {
            "model": state.forecast_model.split(" ")[0],
            "ci_pct": int(state.forecast_ci * 100),
            "years": list(fc.forecast_years),
            "distances": list(fc.forecast_distances),
            "lower": list(fc.forecast_lower),
            "upper": list(fc.forecast_upper),
        }

    summary = [f"Transect #{tid}"]
    if cl:
        summary.append(f"EPR: {cl.epr:+.2f} m/yr  |  LRR: {cl.lrr:+.2f} m/yr")
    if ts and ts.theilsen is not None:
        summary.append(f"TSR: {ts.theilsen:+.2f} m/yr")
    if rs and rs.ransac is not None:
        summary.append(f"RANSAC: {rs.ransac:+.2f} m/yr")
    if bp and bp.breakpoints:
        last = bp.breakpoints[-1]
        summary.append(f"Break Year: {int(last.year)} → Post: {last.rate_after:+.2f} m/yr")

    return {
        "transect_id": tid,
        "traces": traces,
        "breaks": breaks,
        "forecast": forecast,
        "summary": "   |   ".join(summary),
    }


def diagnostics(state: Session) -> dict | None:
    r = state.results
    s_list = state.series_list
    if not r or not s_list:
        return None

    classic = r.get("classic", [])
    theilsen = r.get("theilsen", [])
    ransac = r.get("ransac", [])
    breakpt = r.get("breakpoint", [])

    # Error metrics (RMSE/MAE/BIC) are part of the *evaluation* stage: they are
    # only computed once the user has run Rank Methods (the Scorecard). Until
    # then the Diagnostics view shows just rate + R² (the cheap byproduct of the
    # analysis fits). This keeps analysis lean and computes error metrics once.
    with_errors = state.scorecard is not None

    M = {k: {"rates": [], "r2s": [], "rmses": [], "maes": [], "bics": []}
         for k in ("lrr", "ts", "rs", "bp", "epr")}
    n_breaks_total = 0
    n_outliers_total = 0

    def _push(bucket, rate, d, y, sst, n, k=2, r2_stored=None):
        """Record fit stats for one method on one transect.

        R² is the value already computed at analysis time (`r2_stored`) when
        available — the single source of truth, so the number here always matches
        the attribute table / CSV export. When no stored R² exists (EPR,
        Breakpoint), R² is computed from `y`. RMSE/BIC are *derived* from that R²
        (SSE = SST·(1−R²)) and MAE measured from `y` — but only when
        `with_errors` (i.e. Rank Methods has been run); otherwise just rate + R².
        """
        if r2_stored is not None:
            r2 = float(max(0.0, min(1.0, r2_stored)))
            sse = sst * (1.0 - r2)
        else:
            sse = float(np.sum((d - y) ** 2))
            r2 = float(max(0.0, min(1.0, 1.0 - sse / sst)))
        bucket["rates"].append(rate)
        bucket["r2s"].append(r2)
        if with_errors:
            bucket["rmses"].append(float(np.sqrt(max(sse, 0.0) / n)))
            bucket["maes"].append(float(np.mean(np.abs(d - y))))
            bucket["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + k * np.log(n)))

    for i, s in enumerate(s_list):
        years = np.array(s.years()); d = np.array(s.distances); n = len(years)
        if n < 2:
            continue
        sst = float(np.sum((d - np.mean(d)) ** 2)) or 1e-10

        cl = classic[i] if i < len(classic) else None
        if cl and cl.lrr is not None and not math.isnan(cl.lrr):
            res = st.linregress(years, d)
            y = res.slope * years + res.intercept
            _push(M["lrr"], cl.lrr, d, y, sst, n, r2_stored=cl.lrr_r2)

        ts = theilsen[i] if i < len(theilsen) else None
        if ts and ts.theilsen is not None and not math.isnan(ts.theilsen):
            res = st.theilslopes(d, years, alpha=0.90)
            y = ts.theilsen * years + res.intercept
            _push(M["ts"], ts.theilsen, d, y, sst, n, r2_stored=ts.theilsen_r2)

        rs = ransac[i] if i < len(ransac) else None
        if rs and rs.ransac is not None and not math.isnan(rs.ransac):
            if rs.ransac_outliers:
                n_outliers_total += rs.ransac_outliers
            # Best-fit intercept for the RANSAC slope (for MAE only); R²/RMSE/BIC
            # come from the stored ransac_r2.
            intercept = float(np.mean(d - rs.ransac * years))
            y = rs.ransac * years + intercept
            _push(M["rs"], rs.ransac, d, y, sst, n, r2_stored=rs.ransac_r2)

        if cl and cl.epr is not None and not math.isnan(cl.epr):
            # EPR line passes through both endpoints by definition; no stored R².
            y = cl.epr * (years - years[0]) + d[0]
            _push(M["epr"], cl.epr, d, y, sst, n)

        bp = breakpt[i] if i < len(breakpt) else None
        if bp:
            overall = bp.overall_rate if bp.overall_rate is not None else (cl.lrr if cl else 0.0)
            if bp.breakpoints:
                n_breaks_total += 1
                idx = [int(np.argmin(np.abs(years - b.year))) for b in bp.breakpoints]
                cuts = [0] + sorted(idx) + [n]
                y = np.zeros_like(d)
                for c in range(len(cuts) - 1):
                    sx = years[cuts[c]:cuts[c+1]]; sy = d[cuts[c]:cuts[c+1]]
                    if len(sx) >= 2:
                        rr = st.linregress(sx, sy)
                        y[cuts[c]:cuts[c+1]] = rr.slope * sx + rr.intercept
                    else:
                        y[cuts[c]:cuts[c+1]] = sy
                k = 2 * (len(cuts) - 1) + len(idx)
            else:
                res = st.linregress(years, d)
                y = res.slope * years + res.intercept
                k = 2
            # Breakpoint has no single stored R² (piecewise); compute from the fit.
            _push(M["bp"], overall, d, y, sst, n, k=k)

    def avg(lst, d=2):
        return f"{np.mean(lst):.{d}f}" if lst else "—"

    rows = [
        {"model": "Classic Endpoint Rate (EPR)", "rate": avg(M["epr"]["rates"]), "r2": avg(M["epr"]["r2s"], 3),
         "rmse": avg(M["epr"]["rmses"]) + " m", "mae": avg(M["epr"]["maes"]) + " m", "bic": avg(M["epr"]["bics"], 1),
         "comp": "2 end points"},
        {"model": "Linear Regression (LRR)", "rate": avg(M["lrr"]["rates"]), "r2": avg(M["lrr"]["r2s"], 3),
         "rmse": avg(M["lrr"]["rmses"]) + " m", "mae": avg(M["lrr"]["maes"]) + " m", "bic": avg(M["lrr"]["bics"], 1),
         "comp": "Single line (1 era)"},
        {"model": "Theil-Sen Robust Estimator", "rate": avg(M["ts"]["rates"]), "r2": avg(M["ts"]["r2s"], 3),
         "rmse": avg(M["ts"]["rmses"]) + " m", "mae": avg(M["ts"]["maes"]) + " m", "bic": avg(M["ts"]["bics"], 1),
         "comp": "Median pairwise slopes (29% breakdown)"},
        {"model": "RANSAC Robust Regressor", "rate": avg(M["rs"]["rates"]), "r2": avg(M["rs"]["r2s"], 3),
         "rmse": avg(M["rs"]["rmses"]) + " m", "mae": avg(M["rs"]["maes"]) + " m", "bic": avg(M["rs"]["bics"], 1),
         "comp": f"{n_outliers_total} outliers filtered"},
        {"model": "Breakpoint Regression (SHIFT)", "rate": avg(M["bp"]["rates"]), "r2": avg(M["bp"]["r2s"], 3),
         "rmse": avg(M["bp"]["rmses"]) + " m", "mae": avg(M["bp"]["maes"]) + " m", "bic": avg(M["bp"]["bics"], 1),
         "comp": f"{n_breaks_total} shifts detected"},
    ]

    mean_lrr = np.mean(M["lrr"]["rmses"]) if M["lrr"]["rmses"] else 0.0
    mean_bp = np.mean(M["bp"]["rmses"]) if M["bp"]["rmses"] else 0.0
    improvement = (100 * (mean_lrr - mean_bp) / max(mean_lrr, 1e-5)) if mean_lrr > 0 else 0.0

    return {
        "n_transects": len(s_list),
        "rows": rows,
        "rmse_improvement": round(improvement, 1),
        "has_errors": with_errors,
    }


def summary_stats(state: Session) -> dict | None:
    r = state.results
    classic = r.get("classic", [])
    breakpt = r.get("breakpoint", [])
    if not classic:
        return None

    eprs = [x.epr for x in classic if x and x.epr is not None and not math.isnan(x.epr)]
    lrrs = [x.lrr for x in classic if x and x.lrr is not None and not math.isnan(x.lrr)]
    bps = [x.overall_rate for x in breakpt if x and x.overall_rate is not None and not math.isnan(x.overall_rate)]

    n_eroding = sum(1 for e in eprs if e < 0)
    pct = (n_eroding / len(eprs) * 100) if eprs else 0.0

    return {
        "total_transects": len(state.series_list),
        "eroding": f"{pct:.1f}% ({n_eroding} transects)",
        "mean_epr": f"{np.mean(eprs):+.2f} m/yr" if eprs else "—",
        "mean_lrr": f"{np.mean(lrrs):+.2f} m/yr" if lrrs else "—",
        "mean_bp": f"{np.mean(bps):+.2f} m/yr" if bps else "—",
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


def scorecard_view(state: Session) -> dict:
    """Model scorecard for the frontend: headline, leaderboard rows, winner distribution."""
    sc = state.scorecard
    if not sc:
        return {"available": False, "headline": "", "recommended": None, "rows": [],
                "distribution": [], "n_participating": 0, "n_total": 0, "thresholds": {}}

    def fmt(v, unit="", d=2):
        if v is None:
            return "—"
        return f"{v:.{d}f}{unit}"

    rows = []
    for r in sc["rows"]:
        rows.append({
            "method": r["method"],
            "holdout_rmse": fmt(r.get("holdout_rmse"), " m"),
            "holdout_mae": fmt(r.get("holdout_mae"), " m"),
            # Keep legacy aliases for any old clients
            "loocv_rmse": fmt(r.get("holdout_rmse"), " m"),
            "roll_rmse": fmt(r.get("holdout_mae"), " m"),
            "mae": fmt(r.get("holdout_mae"), " m"),
            "r2": fmt(r["r2"], "", 3),
            "bic": fmt(r["bic"], "", 1),
            "coverage": f"{r['coverage']}/{sc['n_participating']}",
            "win_pct": f"{r['win_pct']:.0f}%",
            "is_recommended": r["method"] == sc.get("recommended"),
        })

    # Winner distribution (only methods that won at least one transect)
    dist = [{"method": r["method"], "wins": r["wins"], "win_pct": r["win_pct"]}
            for r in sc["rows"] if r["wins"] > 0]
    dist.sort(key=lambda d: d["wins"], reverse=True)

    return {
        "available": True,
        "headline": sc["headline"],
        "recommended": sc.get("recommended"),
        "rows": rows,
        "distribution": dist,
        "n_participating": sc["n_participating"],
        "n_total": sc["n_total"],
        "thresholds": sc["thresholds"],
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

