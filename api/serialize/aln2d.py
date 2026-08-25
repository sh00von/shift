"""2D-ALN result serializers for all three ALN tables."""
from __future__ import annotations

import math

from api.session import Session


def _f(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)


def aln2d_summary_rows(state: Session) -> list[dict]:
    if state.aln2d_summary is None or state.aln2d_summary.empty:
        return []
    rows = []
    for _, row in state.aln2d_summary.iterrows():
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
    if state.aln2d_validation is None or state.aln2d_validation.empty:
        return []
    rows = []
    for _, row in state.aln2d_validation.iterrows():
        rows.append({
            "metric_name": str(row.get("metric_name", "")),
            "vs_lrr": str(row.get("vs_lrr", "")),
            "vs_epr": str(row.get("vs_epr", "")),
            "vs_kf": str(row.get("vs_kf", "")),
        })
    return rows


def aln2d_reach_rows(state: Session) -> list[dict]:
    if state.aln2d_reaches is None or state.aln2d_reaches.empty:
        return []
    rows = []
    for _, row in state.aln2d_reaches.iterrows():
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
