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
    rf = r.get("rf", [])

    rows = []
    for i, s in enumerate(state.series_list):
        cl = classic[i] if i < len(classic) else None
        ts = theilsen[i] if i < len(theilsen) else None
        rs = ransac[i] if i < len(ransac) else None
        bp = breakpt[i] if i < len(breakpt) else None
        rfr = rf[i] if i < len(rf) else None
        rows.append({
            "id": s.transect_id,
            "epr": _f(cl.epr if cl else None),
            "lrr": _f(cl.lrr if cl else None),
            "tsr": _f(ts.theilsen if ts else None),
            "ransac": _f(rs.ransac if rs else None),
            "wlr": _f(cl.wlr if cl else None),
            "bp_rate": _f(bp.overall_rate if bp else None),
            "bp_year": _f(bp.breakpoints[-1].year if bp and bp.breakpoints else None, 0),
            "n_brk": str(len(bp.breakpoints) + 1) if bp else "1",
            "rf_rmse": _f(rfr.rf_rmse if rfr else None),
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
    rf_list = r.get("rf", [])

    M = {k: {"rates": [], "r2s": [], "rmses": [], "maes": [], "bics": []}
         for k in ("lrr", "ts", "rs", "bp", "rf", "epr")}
    n_breaks_total = 0
    n_outliers_total = 0

    for i, s in enumerate(s_list):
        years = np.array(s.years()); d = np.array(s.distances); n = len(years)
        if n < 2:
            continue
        sst = float(np.sum((d - np.mean(d)) ** 2)) or 1e-10

        cl = classic[i] if i < len(classic) else None
        if cl and cl.lrr is not None and not math.isnan(cl.lrr):
            res = st.linregress(years, d)
            y = res.slope * years + res.intercept
            sse = float(np.sum((d - y) ** 2))
            M["lrr"]["rates"].append(cl.lrr)
            M["lrr"]["r2s"].append(float(res.rvalue ** 2))
            M["lrr"]["rmses"].append(float(np.sqrt(sse / n)))
            M["lrr"]["maes"].append(float(np.mean(np.abs(d - y))))
            M["lrr"]["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + 2 * np.log(n)))

        ts = theilsen[i] if i < len(theilsen) else None
        if ts and ts.theilsen is not None and not math.isnan(ts.theilsen):
            res = st.theilslopes(d, years, alpha=0.90)
            y = ts.theilsen * years + res.intercept
            sse = float(np.sum((d - y) ** 2))
            M["ts"]["rates"].append(ts.theilsen)
            M["ts"]["r2s"].append(float(max(0.0, min(1.0, 1.0 - sse / sst))))
            M["ts"]["rmses"].append(float(np.sqrt(sse / n)))
            M["ts"]["maes"].append(float(np.mean(np.abs(d - y))))
            M["ts"]["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + 2 * np.log(n)))

        rs = ransac[i] if i < len(ransac) else None
        if rs and rs.ransac is not None and not math.isnan(rs.ransac):
            if rs.ransac_outliers:
                n_outliers_total += rs.ransac_outliers
            y = rs.ransac * (years - years[0]) + d[0]
            sse = float(np.sum((d - y) ** 2))
            M["rs"]["rates"].append(rs.ransac)
            M["rs"]["r2s"].append(float(max(0.0, min(1.0, 1.0 - sse / sst))))
            M["rs"]["rmses"].append(float(np.sqrt(sse / n)))
            M["rs"]["maes"].append(float(np.mean(np.abs(d - y))))
            M["rs"]["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + 2 * np.log(n)))

        if cl and cl.epr is not None and not math.isnan(cl.epr):
            y = cl.epr * (years - years[0]) + d[0]
            sse = float(np.sum((d - y) ** 2))
            M["epr"]["rates"].append(cl.epr)
            M["epr"]["r2s"].append(float(max(0.0, 1.0 - sse / sst)))
            M["epr"]["rmses"].append(float(np.sqrt(sse / n)))
            M["epr"]["maes"].append(float(np.mean(np.abs(d - y))))
            M["epr"]["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + 2 * np.log(n)))

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
                sse = float(np.sum((d - y) ** 2))
                k = 2 * (len(cuts) - 1) + len(idx)
            else:
                res = st.linregress(years, d)
                y = res.slope * years + res.intercept
                sse = float(np.sum((d - y) ** 2)); k = 2
            M["bp"]["rates"].append(overall)
            M["bp"]["r2s"].append(float(max(0.0, min(1.0, 1.0 - sse / sst))))
            M["bp"]["rmses"].append(float(np.sqrt(sse / n)))
            M["bp"]["maes"].append(float(np.mean(np.abs(d - y))))
            M["bp"]["bics"].append(float(n * np.log(max(sse / n, 1e-10)) + k * np.log(n)))

        rf = rf_list[i] if i < len(rf_list) else None
        if rf and rf.rf_rmse is not None:
            rmse = rf.rf_rmse
            M["rf"]["rates"].append((rf.rf_prediction - d[0]) / max(years[-1] - years[0], 0.1) if rf.rf_prediction else (cl.lrr if cl else 0.0))
            M["rf"]["r2s"].append(float(max(0.0, 1.0 - (rmse ** 2) / (sst / n))))
            M["rf"]["rmses"].append(float(rmse))
            M["rf"]["maes"].append(float(rmse * 0.8))
            M["rf"]["bics"].append(float(n * np.log(max(rmse ** 2, 1e-10)) + 4 * np.log(n)))

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
        {"model": "Random Forest Benchmark (ML)", "rate": avg(M["rf"]["rates"]), "r2": avg(M["rf"]["r2s"], 3),
         "rmse": avg(M["rf"]["rmses"]) + " m", "mae": avg(M["rf"]["maes"]) + " m", "bic": avg(M["rf"]["bics"], 1),
         "comp": "200 Trees (Non-linear)"},
    ]

    mean_lrr = np.mean(M["lrr"]["rmses"]) if M["lrr"]["rmses"] else 0.0
    mean_bp = np.mean(M["bp"]["rmses"]) if M["bp"]["rmses"] else 0.0
    improvement = (100 * (mean_lrr - mean_bp) / max(mean_lrr, 1e-5)) if mean_lrr > 0 else 0.0

    return {"n_transects": len(s_list), "rows": rows, "rmse_improvement": round(improvement, 1)}


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
