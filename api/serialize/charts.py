"""Transect time-series chart data serializer."""
from __future__ import annotations

import math

from api.session import Session

FORECAST_COLORS = ["#9333ea", "#f59e0b", "#10b981", "#ef4444", "#0891b2", "#64748b"]


def chart_data(state: Session, tid: int) -> dict | None:
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
            "name": "EKF (fitted curve)", "kind": "line", "dash": "solid",
            "x": ek.fitted_years, "y": ek.fitted_values, "color": "#10b981",
        })
        traces.append({
            "name": f"EKF rate ({ek.ekf:+.2f} m/yr)", "kind": "line", "dash": "dot",
            "x": yrs, "y": [ek.ekf * (y - yrs[0]) + d[0] for y in yrs], "color": "#10b981",
        })

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

    summary = [f"Transect #{tid}"]
    if cl:
        summary.append(f"EPR: {cl.epr:+.2f} m/yr  |  LRR: {cl.lrr:+.2f} m/yr")
    if ek and ek.ekf is not None:
        summary.append(f"EKF: {ek.ekf:+.2f} m/yr")

    return {
        "transect_id": tid,
        "traces": traces,
        "forecast": forecasts[0] if forecasts else None,
        "forecasts": forecasts,
        "summary": "   |   ".join(summary),
    }
