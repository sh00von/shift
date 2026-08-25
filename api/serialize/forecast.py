"""Forecast evaluation view serializer."""
from __future__ import annotations

from api.session import Session


def forecast_eval_view(state: Session) -> dict:
    ev = state.forecast_eval
    if not ev:
        return {"available": False, "rows": [], "best_model": None}

    def _fmt(v, unit=""):
        return f"{v:.2f}{unit}" if v is not None else "—"

    rows = []
    for model, stats in ev.items():
        rows.append({
            "model": model,
            "rmse": _fmt(stats.get("rmse"), " m"),
            "mae": _fmt(stats.get("mae"), " m"),
            "n": stats.get("n", 0),
            "rmse_raw": stats.get("rmse"),
        })

    rows.sort(key=lambda r: (r["rmse_raw"] is None,
                             r["rmse_raw"] if r["rmse_raw"] is not None else 1e9))
    best = rows[0]["model"] if rows and rows[0]["rmse_raw"] is not None else None

    return {
        "available": True,
        "rows": [{k: v for k, v in r.items() if k != "rmse_raw"} for r in rows],
        "best_model": best,
        "n_transects": len(state.series_list),
    }
