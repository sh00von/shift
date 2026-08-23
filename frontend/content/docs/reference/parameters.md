# Parameters

Every tunable lives on the backend `Session` (`api/session.py`) and is patched via
`PATCH /api/session/{sid}/params`. The frontend mirrors them in the Zustand store's `params`.
Defaults below are the `Session` dataclass defaults.

## Data & field mapping

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `date_col` | string \| null | `null` | Shoreline attribute holding the survey date. |
| `date_format` | string | `"auto"` | Parse format (`auto` or `strftime`, e.g. `%d/%m/%Y`). |
| `uncertainty_col` | string \| null | `null` | Attribute holding per-survey positional error (m). |
| `default_uncertainty` | float | `10.0` | Fallback uncertainty (m) when no column is mapped. |

## Transect geometry

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `spacing` | float | `250.0` | Alongshore interval between transects (m). |
| `smoothing` | float | `4000.0` | Baseline-heading smoothing window (m). |
| `transect_length` | float | `8000.0` | Length of each transect (m). |
| `cast_side` | string | `"right"` | Cast direction — `left` or `right` of the baseline. |
| `buffer_distance` | float | `500.0` | Seaward buffer used to synthesise an auto-baseline (m). |

## Method toggles

| Parameter | Type | Default | Method |
|---|---|---|---|
| `run_classic` | bool | `true` | USGS DSAS (EPR/LRR/WLR/NSM/SCE). |
| `run_theilsen` | bool | `true` | Theil-Sen robust rate. |
| `run_ransac` | bool | `true` | RANSAC robust rate. |
| `run_breakpoint` | bool | `true` | Breakpoint / regime-shift detection. |

## Forecast

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `forecast_model` | string | `""` | Driving model for projection. |
| `forecast_horizon` | int | `10` | Years to project forward. |
| `forecast_ci` | float | `0.90` | Confidence level for the uncertainty cone. |

## Map / styling

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `style_metric` | string | `"LRR (m/yr)"` | Metric the rate choropleth colours by. |
| `color_ramp` | string | `"Red-Yellow-Green (DSAS)"` | Choropleth colour ramp. |
| `shoreline_palette` | string | `"turbo"` | Matplotlib colormap for date-coded shorelines. |

## 2D-ALN

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `aln2d_reach_length` | float | `1000.0` | Reach segment length (m). |
| `aln2d_reach_buffer` | float | `1000.0` | Reach clipping buffer (m). |
| `aln2d_search_mask_buffer` | float | `5000.0` | Bank search-mask buffer (m). |

## Scorecard thresholds

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `scorecard_bic_gain` | float | `6.0` | Breakpoint BIC-gain requirement. |
| `scorecard_outlier_z` | float | `2.5` | Standardised-residual outlier threshold. |
| `scorecard_tie_pct` | float | `5.0` | RMSE tie margin (%). |

## Read-only status flags

The params payload also carries `has_shoreline`, `has_baseline`, `has_results`,
`has_aln2d_results`, `has_scorecard`, the original filenames, and the server-side `logs`.
These are set by the backend, not patched by the client.
