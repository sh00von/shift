# Bottom Inspector

The collapsible bottom dock holds five tabs of tabular and diagnostic output. Toggle it from
the Status bar or by opening a layer's attribute table.

![Figure 11: Five-Tab Bottom Inspector Dock Layout](/docs/bottom_inspector_dock.png)

## Attribute table

A spreadsheet of every transect and its rates.

- **Search** by transect ID; **filter** by All / Eroding / Accreting / Changepoints.
- **Sort** by clicking any column header.
- **Columns:** T-ID, EPR, LRR, **Trend**, Theil-Sen, RANSAC, WLR, Post-break rate, Break year,
  Regimes. Rate cells are coloured red (erosion) / green (accretion).
- **Trend** classifies each transect from the LRR **95% confidence interval**: *Erosion* /
  *Accretion* when the CI excludes zero, or ***Stable*** when it includes zero (the rate is not
  statistically significant). Hover the LRR cell to see the CI bounds. This implements
  "report the interval, not the point" — see [DSAS Classic](/docs/methods/dsas-classic).
- **Click a row** to select that transect (highlights on the map, opens the Inspector).

## Diagnostics

Cross-model goodness-of-fit, one row per method. Right after **Run Analysis** it shows just the
mean rate and mean **R²** (R² is computed as a free byproduct of each fit). The error metrics —
**residual RMSE, MAE, BIC** — are part of the *evaluation* stage and appear only **after you run
[Rank Methods](/docs/guide/rank-methods)**, so nothing is computed twice and analysis stays
lean. Once available, a summary line quantifies how much the breakpoint model reduces RMSE
versus static linear regression, and the breakpoint row is highlighted.

> **In-sample vs out-of-sample.** These Diagnostics (including the RMSE/MAE/BIC unlocked by
> Rank Methods) are **in-sample** fit statistics — how well each method fits the data it was
> trained on (more flexible models will always look better). They are *not* the same as the
> **Model Scorecard**, which measures true **out-of-sample** predictive skill via holdout hindcasting ($1 \dots N-1 \rightarrow N$).
> When the two disagree, trust the Scorecard for choosing a method to forecast with; use
> Diagnostics only to describe fit.

## Model Scorecard

The holdout backtesting leaderboard produced by [Rank Methods](/docs/guide/rank-methods):

- headline recommended method,
- a table of Holdout RMSE, Holdout MAE, in-sample R², BIC, coverage, and win % per method,
- the guardrail thresholds used, and
- a win-count distribution chart.

## 2D-ALN Morphodynamics

The output of the [2D-ALN engine](/docs/guide/2d-aln): the areal budget summary (eroded/
accreted km² and rates per epoch pair) and the reach-level table (net/erosion/accretion m/yr
with 1D DSAS benchmarks). Empty until you run 2D-ALN.

## Console

A timestamped, filterable event log of everything the app does. Each entry has a coloured dot
by level (error / warn / success / info). Search the log text, copy all entries, or clear it.
The log is a circular buffer of the most recent 500 entries; the Status bar shows the current
count.
