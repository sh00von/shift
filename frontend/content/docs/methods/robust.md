# Robust Rates: Theil-Sen & RANSAC

Ordinary regression (LRR) is pulled around by outlier surveys — a mis-digitised shoreline, a
tidal spike, cloud shadow in satellite imagery. The robust methods resist that. Both are in
`shift/stats/robust.py`.

![Figure 14: Robust Estimators (Theil-Sen & RANSAC) vs. OLS Under Outlier Disturbance](/docs/robust_vs_ols.png)

## Theil-Sen estimator

`TheilSenMethod` computes the **median of the slopes** between every pair of survey points:

```
TheilSen = median{ (dⱼ − dᵢ) / (tⱼ − tᵢ)  for all i < j }
```

- Reported with a pseudo-**R²** (from SSE/SST).
- Has a ~29.3% breakdown point — up to ~29% of the surveys can be arbitrarily corrupt before
  the estimate breaks down.
- No tuning needed; deterministic.

Use it when you suspect a few bad surveys but don't want to tune anything.

## RANSAC regressor

`RansacMethod` (RANdom SAmple Consensus) repeatedly fits a line to a random minimal subset,
counts how many points agree within a residual threshold, and keeps the best consensus fit.

- Residual threshold: **2.5 × median survey uncertainty** (or **20 m** when no
  uncertainty data is present), with a **10 m floor**.
- Reports the consensus slope and the **count of detected outliers**.
- Best when outliers are a distinct minority (digitisation blunders, cloud artefacts).

## Choosing between them

| | Theil-Sen | RANSAC |
|---|---|---|
| Mechanism | Median pairwise slope | Consensus subset fit |
| Tuning | None | Residual threshold |
| Best for | Scattered noise, few bad points | A clear minority of gross outliers |
| Output extras | pseudo-R² | outlier count |

> In the [Scorecard](/docs/methods/scorecard), robust methods are only counted as candidates
> where genuine outliers are detected (`outlier |z|` guardrail) — on clean data, LRR is
> preferred because the robust methods offer no advantage there.
