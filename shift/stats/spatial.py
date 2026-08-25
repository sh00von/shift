"""Spatial autocorrelation (Moran's I) and rate smoothing for transect arrays."""
from __future__ import annotations

import math
import numpy as np
from scipy import stats as st


def morans_i(
    rates: list[float | None],
    *,
    queen: bool = False,  # reserved; always uses linear-neighbour weights
) -> dict:
    """
    Compute Moran's I for a 1-D ordered array of transect rates.

    Weights are first-order linear contiguity (each transect neighbours the
    two adjacent ones).  Missing / NaN values are excluded row- and
    column-wise; their neighbours are connected directly.

    Returns
    -------
    dict with keys: I, expected_I, z_score, p_value, interpretation
    """
    vals = np.array([float(r) if r is not None else np.nan for r in rates])
    mask = ~np.isnan(vals)
    x = vals[mask]
    n = len(x)

    if n < 4:
        return {"I": None, "expected_I": None, "z_score": None, "p_value": None, "interpretation": "insufficient data"}

    # Build contiguity weight matrix for the *compressed* (non-NaN) sequence
    W = np.zeros((n, n))
    for i in range(n):
        if i > 0:
            W[i, i - 1] = 1.0
        if i < n - 1:
            W[i, i + 1] = 1.0

    w_sum = W.sum()
    xbar = x.mean()
    z = x - xbar
    numerator = (z @ W @ z) * n
    denominator = (z @ z) * w_sum

    I = float(numerator / denominator) if denominator != 0 else 0.0
    E_I = -1.0 / (n - 1)

    # Variance under normality assumption (Cliff & Ord 1981)
    s1 = 0.5 * ((W + W.T) ** 2).sum()
    s2 = ((W.sum(axis=1) + W.sum(axis=0)) ** 2).sum()
    s0 = w_sum
    n2 = n * n
    var_I = (
        n * (n2 - 3 * n + 3) * s1 - n * s2 + 3 * s0 ** 2
    ) / (
        (n - 1) * (n2 - n) * s0 ** 2
    ) - E_I ** 2

    z_score = float((I - E_I) / math.sqrt(var_I)) if var_I > 0 else 0.0
    p_value = float(2 * (1 - st.norm.cdf(abs(z_score))))

    if p_value < 0.05:
        interpretation = "Clustered" if I > E_I else "Dispersed"
    else:
        interpretation = "Random"

    return {
        "I": round(I, 4),
        "expected_I": round(E_I, 4),
        "z_score": round(z_score, 3),
        "p_value": round(p_value, 4),
        "interpretation": interpretation,
    }


def smooth_rates(
    transect_ids: list[int],
    rates: list[float | None],
    window: int = 3,
) -> list[dict]:
    """
    Apply a centred moving-average smoother to transect rates.

    Parameters
    ----------
    transect_ids : aligned list of transect IDs
    rates        : raw rate values (None = missing)
    window       : half-window in number of transects (total width = 2*window+1)

    Returns
    -------
    list of {transect_id, smoothed_rate}
    """
    arr = np.array([float(r) if r is not None else np.nan for r in rates])
    n = len(arr)
    smoothed = np.full(n, np.nan)
    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        chunk = arr[lo:hi]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) > 0:
            smoothed[i] = float(valid.mean())

    return [
        {"transect_id": tid, "smoothed_lrr": None if math.isnan(v) else round(v, 4)}
        for tid, v in zip(transect_ids, smoothed)
    ]
