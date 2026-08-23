"""Out-of-sample holdout scorecard for shoreline-rate methods.

Evaluates every rate/position method on a strict holdout / hindcast protocol:
  • Training set: Surveys 1 to N-1 (e.g. 1995–2020)
  • Test target : Latest survey N (e.g. 2025)

Each method is fit on the historical training surveys, projects forward to the latest
survey date, and is evaluated against the real measured shoreline position. A domain-aware
guarded rule selects the winning method per transect and headline recommendation.

Competitors: EPR, LRR, WLR, Theil-Sen, RANSAC, Kalman, Breakpoint.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np
from scipy import stats as st

from shift.models import TransectSeries

ProgressCB = Callable[[str, float], None]

DEFAULT_THRESHOLDS = {
    "bic_gain": 6.0,      # Kass–Raftery "strong" evidence for a regime shift
    "outlier_z": 2.5,     # |standardised residual| above which a survey is an outlier
    "tie_pct": 5.0,       # winners within this % of the best error count as a tie
}

# (name, min_train_points, complexity_rank) — lower rank = simpler = preferred on ties.
METHODS: list[tuple[str, int, int]] = [
    ("EPR", 2, 0),
    ("LRR", 2, 1),
    ("WLR", 2, 2),
    ("Theil-Sen", 2, 3),
    ("RANSAC", 3, 4),
    ("Kalman", 2, 5),
    ("Breakpoint", 4, 6),
]
COMPLEXITY = {name: rank for name, _, rank in METHODS}
MIN_TRAIN = {name: mt for name, mt, _ in METHODS}
ALWAYS_ELIGIBLE = {"EPR", "LRR", "WLR", "Kalman"}


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
    if name == "Theil-Sen":
        res = st.theilslopes(y, x)
        return float(res[0] * t + res[1])
    if name == "RANSAC":
        from sklearn.linear_model import RANSACRegressor, LinearRegression
        m = RANSACRegressor(estimator=LinearRegression(), min_samples=max(2, len(x) // 2), random_state=0)
        m.fit(x.reshape(-1, 1), y)
        return float(m.predict([[t]])[0])
    if name == "Kalman":
        return _kalman_predict(x, y, w, t)
    if name == "Breakpoint":
        return _breakpoint_predict(x, y, t)
    raise ValueError(name)


def _kalman_predict(x: np.ndarray, y: np.ndarray, w: np.ndarray, t: float) -> float:
    """Linear Kalman filter over the training surveys, projected to the target year."""
    slope, intercept = _ols(x, y)
    resid = y - (slope * x + intercept)
    resid_var = float(np.sum(resid ** 2) / max(len(x) - 2, 1))
    ss_x = float(np.sum((x - x.mean()) ** 2)) or 1.0
    state = np.array([y[0], slope], dtype=float)
    P = np.array([[max(w[0], 1.0) ** 2, 0.0], [0.0, max(resid_var / ss_x, (abs(slope) * 0.5 + 0.05) ** 2)]])
    H = np.array([[1.0, 0.0]])
    q_rate = max(resid_var / ss_x * 0.1, (abs(slope) * 0.02 + 0.01) ** 2)

    def predict_step(state, P, dt):
        F = np.array([[1.0, dt], [0.0, 1.0]])
        Q = np.array([[q_rate * dt ** 3 / 3.0, q_rate * dt ** 2 / 2.0],
                      [q_rate * dt ** 2 / 2.0, q_rate * dt]])
        return F @ state, F @ P @ F.T + Q

    for k in range(1, len(x)):
        dt = float(x[k] - x[k - 1]) or 1e-6
        state, P = predict_step(state, P, dt)
        R = np.array([[max(w[k], 1.0) ** 2]])
        innov = y[k] - (H @ state)[0]
        S = (H @ P @ H.T + R)[0, 0]
        K = (P @ H.T / S).reshape(2)
        state = state + K * innov
        P = (np.eye(2) - np.outer(K, H)) @ P
    return float(state[0] + state[1] * (t - x[-1]))


def _breakpoint_predict(x: np.ndarray, y: np.ndarray, t: float) -> float:
    """Single-breakpoint piecewise-linear predictor (BIC-selected vs no break)."""
    n = len(x)
    s, b = _ols(x, y)
    best = (None, s, b)  # (break_index, slope, intercept) for no-break
    base_sse = float(np.sum((y - (s * x + b)) ** 2))
    best_bic = n * math.log(max(base_sse / n, 1e-10)) + 2 * math.log(n)
    for k in range(2, n - 1):  # need ≥2 points each side
        s1, b1 = _ols(x[:k], y[:k])
        s2, b2 = _ols(x[k:], y[k:])
        sse = float(np.sum((y[:k] - (s1 * x[:k] + b1)) ** 2) + np.sum((y[k:] - (s2 * x[k:] + b2)) ** 2))
        bic = n * math.log(max(sse / n, 1e-10)) + 5 * math.log(n)
        if bic < best_bic:
            best_bic = bic
            best = (k, s2, b2)  # predict from the later (most recent) segment
    _, sl, ic = best
    return float(sl * t + ic)


# ── In-sample stats (for the R²/BIC columns + Breakpoint eligibility) ──

def _insample(name: str, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    """Return (R², BIC) of the method fit on the whole series."""
    n = len(x)
    sst = float(np.sum((y - y.mean()) ** 2)) or 1e-10
    if name == "Breakpoint":
        k, sse = _breakpoint_fit_sse(x, y)
        r2 = max(0.0, min(1.0, 1.0 - sse / sst))
        bic = n * math.log(max(sse / n, 1e-10)) + k * math.log(n)
        return r2, bic
    yhat = np.array([_safe_predict(name, x, y, w, xi) for xi in x])
    sse = float(np.sum((y - yhat) ** 2))
    r2 = max(0.0, min(1.0, 1.0 - sse / sst))
    kparams = {"EPR": 2, "LRR": 2, "WLR": 2, "Theil-Sen": 2, "RANSAC": 2, "Kalman": 3}.get(name, 2)
    bic = n * math.log(max(sse / n, 1e-10)) + kparams * math.log(n)
    return r2, bic


def _breakpoint_fit_sse(x: np.ndarray, y: np.ndarray) -> tuple[int, float]:
    n = len(x)
    s, b = _ols(x, y)
    base_sse = float(np.sum((y - (s * x + b)) ** 2))
    best_bic = n * math.log(max(base_sse / n, 1e-10)) + 2 * math.log(n)
    best = (2, base_sse)
    for k in range(2, n - 1):
        s1, b1 = _ols(x[:k], y[:k]); s2, b2 = _ols(x[k:], y[k:])
        sse = float(np.sum((y[:k] - (s1 * x[:k] + b1)) ** 2) + np.sum((y[k:] - (s2 * x[k:] + b2)) ** 2))
        bic = n * math.log(max(sse / n, 1e-10)) + 5 * math.log(n)
        if bic < best_bic:
            best_bic = bic; best = (5, sse)
    return best


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
    if sd > 0 and float(np.max(np.abs(resid))) / sd > outlier_z:
        return True
    try:
        from sklearn.linear_model import RANSACRegressor, LinearRegression
        m = RANSACRegressor(estimator=LinearRegression(), random_state=0).fit(x.reshape(-1, 1), y)
        return bool((~m.inlier_mask_).sum() >= 1)
    except Exception:
        return False


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
    n_train = len(x_train)

    has_outliers = _outliers_present(x_train, y_train, th["outlier_z"])
    per: dict[str, dict] = {}

    for name, mt, _ in METHODS:
        if n_train < mt:
            per[name] = {"error": None, "abs_error": None, "sq_error": None, "r2": None, "bic": None, "scoreable": False, "eligible": False}
            continue

        pred = _safe_predict(name, x_train, y_train, w_train, x_test)
        if math.isnan(pred):
            per[name] = {"error": None, "abs_error": None, "sq_error": None, "r2": None, "bic": None, "scoreable": False, "eligible": False}
            continue

        err = y_test - pred
        abs_err = abs(err)
        sq_err = err ** 2
        r2, bic = _insample(name, x, y, w)
        per[name] = {
            "error": float(err),
            "abs_error": float(abs_err),
            "sq_error": float(sq_err),
            "r2": r2,
            "bic": bic,
            "scoreable": True,
            "eligible": True,
        }

    # ── Guarded eligibility ──
    lrr = per["LRR"]
    lrr_err = lrr["abs_error"]
    lrr_bic = lrr["bic"]

    for name in ("Theil-Sen", "RANSAC"):
        if per[name]["scoreable"] and not has_outliers:
            per[name]["eligible"] = False

    bp = per["Breakpoint"]
    if bp["scoreable"] and bp["bic"] is not None and lrr_bic is not None and lrr_err is not None:
        delta_bic = lrr_bic - bp["bic"]  # positive → breakpoint improves BIC
        beats_lrr = bp["abs_error"] is not None and bp["abs_error"] < lrr_err
        bp["eligible"] = bool(delta_bic >= th["bic_gain"] and beats_lrr)
        bp["delta_bic"] = round(float(delta_bic), 2)

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
    acc = {name: {"sq_errors": [], "abs_errors": [], "r2": [], "bic": [], "scored": 0, "wins": 0}
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
                if m["r2"] is not None: a["r2"].append(m["r2"])
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
            "r2": _m(a["r2"]),
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
