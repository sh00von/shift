"""Out-of-sample holdout scorecard for shoreline-rate methods.

Evaluates every rate/position method on a strict holdout / hindcast protocol:
  • Training set: Surveys 1 to N-1 (e.g. 1995–2020)
  • Test target : Latest survey N (e.g. 2025)

Each method is fit on the historical training surveys, projects forward to the latest
survey date, and is evaluated against the real measured shoreline position. A domain-aware
guarded rule selects the winning method per transect and headline recommendation.

Competitors: EPR, LRR, WLR, EKF.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np
from scipy import stats as st

from shift.models import TransectSeries
from shift.forecast._utils import strip_outliers

ProgressCB = Callable[[str, float], None]

DEFAULT_THRESHOLDS = {
    "outlier_z": 2.5,     # |standardised residual| above which a survey is an outlier
    "tie_pct": 5.0,       # winners within this % of the best error count as a tie
}

# (name, min_train_points, complexity_rank) — lower rank = simpler = preferred on ties.
METHODS: list[tuple[str, int, int]] = [
    ("EPR", 2, 0),
    ("LRR", 2, 1),
    ("WLR", 2, 2),
    ("EKF", 2, 3),
]
COMPLEXITY = {name: rank for name, _, rank in METHODS}
MIN_TRAIN = {name: mt for name, mt, _ in METHODS}
ALWAYS_ELIGIBLE = {"EPR", "LRR", "WLR", "EKF"}


# ── Per-method position predictors: given training (years, dist, unc), predict at target year ──

def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    r = st.linregress(x, y)
    return float(r.slope), float(r.intercept)


def _predict(name: str, x: np.ndarray, y: np.ndarray, w: np.ndarray, t: float) -> float:
    if name == "EPR":
        slope = (y[-1] - y[0]) / (x[-1] - x[0]) if x[-1] != x[0] else 0.0
        return float(y[0] + slope * (t - x[0]))
    if name == "LRR":
        s, b = _ols(x, y)
        return float(s * t + b)
    if name == "WLR":
        wt = 1.0 / np.clip(w, 1e-6, None) ** 2
        s, b = np.polyfit(x, y, 1, w=np.sqrt(wt))
        return float(s * t + b)
    if name == "EKF":
        return _ekf_predict(x, y, w, t)
    raise ValueError(name)


def _ekf_predict(x: np.ndarray, y: np.ndarray, w: np.ndarray, t: float) -> float:
    """EKF forward pass on training data, then project to target year."""
    import warnings
    slope, intercept = _ols(x, y)
    resid = y - (slope * x + intercept)
    resid_var = float(np.sum(resid ** 2) / max(len(x) - 2, 1))
    ss_x = float(np.sum((x - x.mean()) ** 2)) or 1.0
    w_safe = np.maximum(w, 0.5)
    state = np.array([intercept + slope * x[0], slope], dtype=float)
    q_vel = max(resid_var / ss_x * 0.1, (abs(slope) * 0.02 + 0.01) ** 2)
    P = np.array([[w_safe[0] ** 2, 0.0], [0.0, q_vel * 10]])
    H = np.array([[1.0, 0.0]])
    for k in range(1, len(x)):
        dt = float(x[k] - x[k - 1]) or 1e-6
        F = np.array([[1.0, dt], [0.0, 1.0]])
        Q = np.array([[q_vel * dt ** 3 / 3, q_vel * dt ** 2 / 2],
                      [q_vel * dt ** 2 / 2, q_vel * dt]])
        state = F @ state
        P = F @ P @ F.T + Q
        R = np.array([[w_safe[k] ** 2]])
        S = (H @ P @ H.T + R)[0, 0]
        K = (P @ H.T / S).reshape(2)
        state = state + K * (y[k] - (H @ state)[0])
        P = (np.eye(2) - np.outer(K, H)) @ P
    dt_pred = float(t - x[-1])
    return float(state[0] + state[1] * dt_pred)


# ── In-sample stats (BIC only) ──

def _insample(name: str, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """Return BIC of the method fit on the whole series."""
    n = len(x)
    yhat = np.array([_safe_predict(name, x, y, w, xi) for xi in x])
    sse = float(np.sum((y - yhat) ** 2))
    kparams = {"EPR": 2, "LRR": 2, "WLR": 2, "EKF": 3}.get(name, 2)
    return n * math.log(max(sse / n, 1e-10)) + kparams * math.log(n)


def _safe_predict(name: str, x: np.ndarray, y: np.ndarray, w: np.ndarray, t: float) -> float:
    try:
        return _predict(name, x, y, w, t)
    except Exception:
        return float("nan")


def _outliers_present(x: np.ndarray, y: np.ndarray, outlier_z: float) -> bool:
    if len(x) < 3:
        return False
    s, b = _ols(x, y)
    resid = y - (s * x + b)
    sd = float(np.std(resid))
    return sd > 0 and float(np.max(np.abs(resid))) / sd > outlier_z


# ── Holdout evaluation of one transect (Train on 1..N-1, Test on N) ──

def _score_transect(series: TransectSeries, th: dict) -> dict | None:
    x = np.asarray(series.years(), float)
    y = np.asarray(series.distances, float)
    w = np.asarray(series.uncertainties, float)
    n = len(x)
    if n < 3:
        return None
    order = np.argsort(x)
    x, y, w = x[order], y[order], w[order]

    x_train, y_train, w_train = x[:-1], y[:-1], w[:-1]
    x_test, y_test = float(x[-1]), float(y[-1])

    has_outliers = _outliers_present(x_train, y_train, th["outlier_z"])

    # Strip positional outliers from training window before fitting any model.
    # Uses the same MAD-based filter as the forecast modules — at least 4 clean
    # training points must remain, otherwise the raw training set is kept.
    _train_series = series.__class__(
        transect_id=series.transect_id,
        dates=series.dates[:-1],
        distances=list(y_train),
        uncertainties=list(w_train),
    )
    _clean = strip_outliers(_train_series)
    if len(_clean) >= 2:
        x_train = np.asarray(_clean.years(), float)
        y_train = np.asarray(_clean.distances, float)
        w_train = np.asarray(_clean.uncertainties, float)

    n_train = len(x_train)
    per: dict[str, dict] = {}

    for name, mt, _ in METHODS:
        if n_train < mt:
            per[name] = {"error": None, "abs_error": None, "sq_error": None, "bic": None, "scoreable": False, "eligible": False}
            continue

        pred = _safe_predict(name, x_train, y_train, w_train, x_test)
        if math.isnan(pred):
            per[name] = {"error": None, "abs_error": None, "sq_error": None, "bic": None, "scoreable": False, "eligible": False}
            continue

        err = y_test - pred
        abs_err = abs(err)
        sq_err = err ** 2
        bic = _insample(name, x, y, w)
        per[name] = {
            "error": float(err),
            "abs_error": float(abs_err),
            "sq_error": float(sq_err),
            "bic": bic,
            "scoreable": True,
            "eligible": True,
        }

    # ── Winner (lowest holdout absolute error, tie → simpler complexity) ──
    cands = []
    for name, _, _ in METHODS:
        m = per[name]
        if m["scoreable"] and m["eligible"] and m["abs_error"] is not None:
            cands.append((name, m["abs_error"]))

    winner = None
    if cands:
        best_err = min(err for _, err in cands)
        tie_bound = best_err * (1.0 + th["tie_pct"] / 100.0)
        tied = [name for name, err in cands if err <= tie_bound]
        winner = min(tied, key=lambda nm: COMPLEXITY[nm])

    return {"n": n, "has_outliers": has_outliers, "winner": winner, "methods": per}



# ── Dataset-level aggregation ──

def build_scorecard(series_list: list[TransectSeries], thresholds: dict | None = None,
                    progress: ProgressCB | None = None) -> dict:
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    total = len(series_list)

    per_tx = []  # {transect_id, winner}
    acc = {name: {"sq_errors": [], "abs_errors": [], "bic": [], "scored": 0, "wins": 0}
           for name, _, _ in METHODS}
    n_participating = 0

    for i, s in enumerate(series_list):
        res = _score_transect(s, th)
        if progress and (i % 10 == 0 or i == total - 1):
            progress(f"Evaluating holdout methods {i + 1}/{total}…", 0.1 + 0.85 * (i + 1) / max(total, 1))
        if res is None:
            continue
        n_participating += 1
        for name, _, _ in METHODS:
            m = res["methods"][name]
            if m["scoreable"]:
                a = acc[name]
                a["scored"] += 1
                if m["sq_error"] is not None: a["sq_errors"].append(m["sq_error"])
                if m["abs_error"] is not None: a["abs_errors"].append(m["abs_error"])
                if m["bic"] is not None: a["bic"].append(m["bic"])
        if res["winner"]:
            acc[res["winner"]]["wins"] += 1
        per_tx.append({"transect_id": int(s.transect_id), "winner": res["winner"]})

    n_won = sum(1 for p in per_tx if p["winner"])

    def _rmse(sq_list):
        return round(float(np.sqrt(np.mean(sq_list))), 2) if sq_list else None

    def _mae(abs_list):
        return round(float(np.mean(abs_list)), 2) if abs_list else None

    def _m(lst):
        return round(float(np.mean(lst)), 3) if lst else None

    rows = []
    for name, _, rank in METHODS:
        a = acc[name]
        wins = a["wins"]
        h_rmse = _rmse(a["sq_errors"])
        h_mae = _mae(a["abs_errors"])
        rows.append({
            "method": name,
            "complexity": rank,
            "holdout_rmse": h_rmse,
            "holdout_mae": h_mae,
            "bic": _m(a["bic"]),
            "coverage": a["scored"],
            "coverage_pct": round(100.0 * a["scored"] / n_participating, 1) if n_participating else 0.0,
            "wins": wins,
            "win_pct": round(100.0 * wins / n_won, 1) if n_won else 0.0,
        })

    # Headline: modal winner; if no majority, flag spatial variability.
    if n_won:
        top = max(rows, key=lambda r: r["wins"])
        share = top["win_pct"]
        if share >= 50.0:
            headline = f"{top['method']} recommended for this dataset ({share:.0f}% of transects)."
            recommended = top["method"]
        else:
            headline = (f"Spatially variable — no single method dominates; "
                        f"{top['method']} leads at {share:.0f}% of transects.")
            recommended = top["method"]
    else:
        headline = "Not enough surveys per transect to rank methods (need ≥3)."
        recommended = None

    return {
        "headline": headline,
        "recommended": recommended,
        "rows": sorted(rows, key=lambda r: (r["holdout_rmse"] is None, r["holdout_rmse"] if r["holdout_rmse"] is not None else 1e9)),
        "per_transect": per_tx,
        "n_participating": n_participating,
        "n_total": total,
        "thresholds": th,
    }
