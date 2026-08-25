"""Attribute table rows and summary statistics serializers."""
from __future__ import annotations

import math
import numpy as np

from api.session import Session
from api.serialize._fmt import fmt


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

        lrr_ci = (
            f"{cl.lrr_ci_low:.2f} to {cl.lrr_ci_high:.2f}"
            if cl and cl.lrr_ci_low is not None and cl.lrr_ci_high is not None
            else "—"
        )

        mk_trend = "—"
        if cl and cl.mk_p is not None and cl.mk_tau is not None:
            if cl.mk_p < 0.05:
                mk_trend = "Erosion★" if cl.mk_tau < 0 else "Accretion★"
            else:
                mk_trend = "Stable"

        rows.append({
            "id": s.transect_id,
            "epr": fmt(cl.epr if cl else None),
            "lrr": fmt(cl.lrr if cl else None),
            "lrr_ci": lrr_ci,
            "trend": trend,
            "wlr": fmt(cl.wlr if cl else None),
            "ekf": fmt(ek.ekf if ek else None),
            "sens": fmt(cl.sens if cl else None),
            "mk_trend": mk_trend,
            "mk_tau": fmt(cl.mk_tau if cl else None, 3),
            "mk_p": fmt(cl.mk_p if cl else None, 3),
        })
    return rows


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
