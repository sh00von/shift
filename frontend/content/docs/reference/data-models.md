# Data Models

The shared result dataclasses live in `shift/models.py`. Every stats method consumes a
`TransectSeries` and returns a `RateResult`; the 2D-ALN engine produces the morphodynamic
models.

## `TransectSeries`

The unit every stats method consumes — one per transect.

| Field | Type | Meaning |
|---|---|---|
| `transect_id` | int | Unique transect identifier. |
| `dates` | list[date] | Survey dates. |
| `distances` | list[float] | Shoreline positions from the baseline (m). |
| `uncertainties` | list[float] | Positional error per survey (m). |
| `years()` | method | Dates as decimal years for regression. |

## `RateResult`

The output container for any method (fields populated depend on which method ran).

- **Classic:** `sce`, `nsm`, `epr`, `lrr`, `lrr_r2`, `wlr`, `wlr_r2`.
- **Changepoint:** `breakpoints` (list of `Breakpoint`), `overall_rate`.
- **Robust:** `theilsen`, `theilsen_r2`, `ransac`, `ransac_outliers`.
- **Forecast:** `forecast_years`, `forecast_distances`, `forecast_lower`, `forecast_upper`.

## `Breakpoint`

A single regime-shift result.

| Field | Meaning |
|---|---|
| `year` | Break year (decimal). |
| `rate_before`, `rate_after` | Segment rates (m/yr). |
| `ci_before`, `ci_after` | Confidence intervals per segment. |

## `MorphodynamicBudget`

Areal change between two epochs (2D-ALN).

| Field | Meaning |
|---|---|
| `from_epoch`, `to_epoch` | Epoch labels. |
| `span_years` | Years between epochs. |
| `eroded_km2`, `accreted_km2` | Areal change. |
| `erosion_rate_km2_yr`, `accretion_rate_km2_yr`, `net_balance_km2_yr` | Rates. |

## `ReachRate`

A 2D-ALN reach with 1D benchmarks.

| Field | Meaning |
|---|---|
| `reach_id`, `length_m` | Reach metadata. |
| `net_2d_m_yr`, `ero_2d_m_yr`, `acc_2d_m_yr` | 2D-ALN rates. |
| `dsas_epr_m_yr`, `dsas_lrr_m_yr`, `dsas_kf_m_yr` | 1D comparison rates. |

## `ALN2DValidationMetric`

| Field | Meaning |
|---|---|
| `metric_name` | Comparison metric (correlation, RMSE, bias). |
| `vs_lrr`, `vs_epr`, `vs_kf` | Score against each 1D method. |
