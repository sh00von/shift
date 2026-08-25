"""Diagnostics tab data serializer: scatter, Moran's I, CBC, Monte Carlo."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as st

from api.session import Session


def diagnostics_data(state: Session, window: int | None = None) -> dict:
    from api.pipeline.diagnostics import compute_spatial
    from shift.stats.cbc import LABEL_COLORS, LABELS

    r = state.results
    classic = r.get("classic", [])

    # --- EPR vs LRR scatter ---
    scatter = []
    epr_vals, lrr_vals = [], []
    for cl in classic:
        if cl and cl.epr is not None and cl.lrr is not None:
            if not (math.isnan(cl.epr) or math.isnan(cl.lrr)):
                epr_vals.append(cl.epr)
                lrr_vals.append(cl.lrr)

    mad_thresh = (1.5 * float(np.median(np.abs(np.array(epr_vals) - np.array(lrr_vals))))
                  if epr_vals and lrr_vals else 0.0)

    for cl in classic:
        if cl and cl.epr is not None and cl.lrr is not None:
            if math.isnan(cl.epr) or math.isnan(cl.lrr):
                continue
            diff = abs(cl.epr - cl.lrr)
            mk_trend = "—"
            if cl.mk_p is not None and cl.mk_tau is not None:
                if cl.mk_p < 0.05:
                    mk_trend = "Erosion★" if cl.mk_tau < 0 else "Accretion★"
                else:
                    mk_trend = "Stable"
            scatter.append({
                "transect_id": cl.transect_id,
                "epr": round(float(cl.epr), 3),
                "lrr": round(float(cl.lrr), 3),
                "mk_trend": mk_trend,
                "is_outlier": bool(diff > mad_thresh and mad_thresh > 0),
            })

    reg_line = None
    if len(scatter) >= 3:
        xs = np.array([p["lrr"] for p in scatter])
        ys = np.array([p["epr"] for p in scatter])
        slope, intercept, r_val, *_ = st.linregress(xs, ys)
        x_range = [float(xs.min()), float(xs.max())]
        reg_line = {
            "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 4),
            "r2": round(float(r_val) ** 2, 4),
            "x": x_range,
            "y": [round(float(intercept) + float(slope) * x, 4) for x in x_range],
        }

    # --- Moran's I + smoothing ---
    spatial = compute_spatial(state, window=window)
    morans = spatial.get("morans", {})
    smoothed = spatial.get("smoothed", [])

    # --- CBC ---
    cbc_rows = state.cbc_results or []
    cbc_summary: dict[str, int] = {lbl: 0 for lbl in LABELS}
    for row in cbc_rows:
        lbl = row.get("label", "Stable")
        cbc_summary[lbl] = cbc_summary.get(lbl, 0) + 1
    cbc_legend = [
        {"label": lbl, "color": LABEL_COLORS[lbl], "count": cbc_summary.get(lbl, 0)}
        for lbl in LABELS
    ]

    # --- Monte Carlo ---
    mc_rows = state.mc_results or []

    return {
        "available": bool(classic),
        "scatter": scatter,
        "reg_line": reg_line,
        "outlier_count": sum(1 for p in scatter if p["is_outlier"]),
        "morans": morans,
        "smoothed": smoothed,
        "smooth_window": state.spatial_smooth_window,
        "cbc_rows": cbc_rows,
        "cbc_summary": cbc_summary,
        "cbc_legend": cbc_legend,
        "mc_rows": mc_rows,
        "mc_available": bool(mc_rows),
    }
