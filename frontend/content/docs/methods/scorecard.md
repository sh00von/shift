# Model Scorecard (Holdout & Hindcasting)

The scorecard (`shift/validation/scorecard.py`, `build_scorecard`) ranks every rate/position
method by **out-of-sample holdout prediction accuracy** and applies domain guardrails to recommend a trustworthy
winner — rather than letting you guess which method to believe.

## Competitors

EPR, LRR, WLR, Theil-Sen, RANSAC, Kalman Filter, and Breakpoint.

## Holdout Evaluation Protocol ($1 \dots N-1 \rightarrow N$)

![Holdout Scorecard Protocol](/docs/holdout_scorecard.png)

For each transect with $N \ge 3$ surveys:

- **Training set** — historical surveys from $1$ to $N-1$ (e.g. 1995–2020).
- **Test target** — the latest held-out survey position at year $N$ (e.g. 2025).
- **Metric** — each model fits on historical training data, projects forward to the latest survey date, and is evaluated against the true measured position:
  $$\text{Error} = y_N - \hat{y}_N$$

## Guarded Eligibility Rules

Not every method is allowed to win everywhere — this prevents complex models from winning by
overfitting:

- **Theil-Sen / RANSAC** — disabled where no outliers are detected (clean data $\Rightarrow$ prefer LRR).
- **Breakpoint** — requires a BIC gain $\ge$ the `bic_gain` threshold (default **6.0**,
  Kass–Raftery "strong" evidence) **and** must beat LRR on holdout error.
- **All others** — eligible whenever scoreable (enough training points).

## Winner Selection

- **Base score** = Absolute Holdout Error $|\text{Error}|$ (lower is better).
- **Ties** (within `tie_pct`, default 5%, of the best error) break toward the **simpler** method by
  complexity rank ($\text{EPR} < \text{LRR} < \text{WLR} < \text{Theil-Sen} < \text{RANSAC} < \text{Kalman} < \text{Breakpoint}$).
- Produces a **per-transect winner** and a dataset-level **headline recommendation** (the
  modal winner).

## Thresholds

| Key | Meaning | Default |
|---|---|---|
| `bic_gain` | Breakpoint BIC-gain requirement | 6.0 |
| `outlier_z` | Standardised-residual threshold for "outlier present" | 2.5 |
| `tie_pct` | Error tie margin (%) | 5.0 |

## Output

The result dictionary drives the [Scorecard tab](/docs/guide/bottom-inspector): `headline`,
`recommended`, per-method `rows` (`holdout_rmse`, `holdout_mae`, $R^2$, BIC, coverage, win %), the
`per_transect` winners, `n_participating`, and the `thresholds` used. The **Best Method** map
layer colours each transect by its winner.

See [Ranking Methods](/docs/guide/rank-methods) for the workflow.

