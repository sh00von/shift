"""
Coastal Behaviour Classification (CBC) — per-transect behavioural label.

Six classes (priority order):
  Interrupted    — structural break detected via Pelt changepoint
  Monotonic Erosion   — MK significant, tau < 0
  Monotonic Accretion — MK significant, tau > 0
  Recovery       — first-half mean < second-half mean (net landward→seaward shift)
                   with MK non-significant
  Cyclical       — dominant autocorrelation at lag 1-3, no trend
  Stable         — fallback
"""
from __future__ import annotations

import numpy as np
from scipy import stats as st

from shift.models import TransectSeries

# Labels exposed to the rest of the system
LABELS = [
    "Monotonic Erosion",
    "Monotonic Accretion",
    "Cyclical",
    "Interrupted",
    "Recovery",
    "Stable",
]

# Colour map for the frontend (hex)
LABEL_COLORS = {
    "Monotonic Erosion":   "#ef4444",   # red-500
    "Monotonic Accretion": "#10b981",   # emerald-500
    "Cyclical":            "#8b5cf6",   # violet-500
    "Interrupted":         "#f59e0b",   # amber-500
    "Recovery":            "#06b6d4",   # cyan-500
    "Stable":              "#94a3b8",   # slate-400
}


def _has_changepoint(d: np.ndarray) -> bool:
    """
    Simple CUSUM-based structural break test.
    Returns True when the residual from a linear fit contains a CUSUM
    that crosses ±1.36/√n (the 5 % critical value of the Kolmogorov-Smirnov
    statistic applied to the normalised CUSUM series).
    """
    n = len(d)
    if n < 5:
        return False
    years = np.arange(n, dtype=float)
    slope, intercept, *_ = st.linregress(years, d)
    resid = d - (intercept + slope * years)
    cusum = np.cumsum(resid - resid.mean())
    cusum_norm = cusum / (resid.std(ddof=1) * np.sqrt(n) + 1e-9)
    threshold = 1.36  # ~5 % KS critical value
    return bool(np.max(np.abs(cusum_norm)) > threshold)


def _autocorr(d: np.ndarray, lag: int) -> float:
    if len(d) <= lag:
        return 0.0
    x = d[:-lag] - d.mean()
    y = d[lag:] - d.mean()
    denom = np.sqrt((x ** 2).sum() * (y ** 2).sum())
    return float((x * y).sum() / denom) if denom > 0 else 0.0


def classify(series: TransectSeries) -> str:
    """Return a CBC label for one transect time series."""
    d = np.array(series.distances)
    n = len(d)
    if n < 3:
        return "Stable"

    years = np.array(series.years())

    # Mann-Kendall
    tau, mk_p = st.kendalltau(years, d)
    mk_sig = mk_p < 0.05

    # 1. Structural break — takes priority
    if n >= 5 and _has_changepoint(d):
        return "Interrupted"

    # 2. Monotonic trends
    if mk_sig and tau < 0:
        return "Monotonic Erosion"
    if mk_sig and tau > 0:
        return "Monotonic Accretion"

    # 3. Recovery: first-half mean lower (more negative = eroded) than second half,
    #    shift ≥ 0.5 std, no overall MK trend
    if n >= 4:
        mid = n // 2
        first_mean = d[:mid].mean()
        second_mean = d[mid:].mean()
        sigma = d.std(ddof=1)
        if sigma > 0 and (second_mean - first_mean) > 0.5 * sigma:
            return "Recovery"

    # 4. Cyclical: significant positive autocorrelation at lag 1, 2, or 3
    if any(_autocorr(d, lag) > 0.4 for lag in range(1, min(4, n - 1))):
        return "Cyclical"

    return "Stable"


def classify_all(series_list: list[TransectSeries]) -> list[dict]:
    """
    Classify every transect.

    Returns
    -------
    list of {transect_id, label, color}
    """
    out = []
    for s in series_list:
        label = classify(s)
        out.append({
            "transect_id": s.transect_id,
            "label": label,
            "color": LABEL_COLORS[label],
        })
    return out
