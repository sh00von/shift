# REST API

All routes are served by `api/main.py`, base URL `http://localhost:8000` (configurable via
`NEXT_PUBLIC_API_BASE` on the frontend). `{sid}` is the session id. Long-running analysis jobs
are **not** here — see [WebSocket Jobs](/docs/reference/websockets).

## Session lifecycle

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/session` | Create a session; returns `{session_id, params}`. |
| GET | `/api/session/{sid}/params` | Fetch current session parameters. |
| PATCH | `/api/session/{sid}/params` | Update parameters (accepts a `ParamPatch`). |
| POST | `/api/session/{sid}/clear` | Reset the session (clear uploads + results). |

## Data loading

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/session/{sid}/upload/shoreline` | Upload a shoreline GeoJSON (multipart file). |
| POST | `/api/session/{sid}/upload/baseline` | Upload a baseline GeoJSON. |
| POST | `/api/session/{sid}/demo` | Load the bundled/synthetic demo dataset. |
| POST | `/api/session/{sid}/auto-baseline` | Generate a baseline by buffering shorelines. |

## Field mapping

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/session/{sid}/shoreline/fields` | Column detection, date parsing preview, detected years. |
| POST | `/api/session/{sid}/shoreline/fields` | Set date/uncertainty mapping (`FieldMappingRequest`). |

## Map layers (GeoJSON)

| Method | Path | Layer |
|---|---|---|
| GET | `/api/session/{sid}/layers/shorelines` | Date-coded shoreline lines. |
| GET | `/api/session/{sid}/layers/baseline` | Baseline line. |
| GET | `/api/session/{sid}/layers/transects` | Orthogonal transect lines. |
| GET | `/api/session/{sid}/layers/choropleth` | Rate-coloured transect envelope + legend. |
| GET | `/api/session/{sid}/layers/forecast` | Forecast line + uncertainty ribbon. |
| GET | `/api/session/{sid}/layers/best_method` | Transects coloured by winning method. |
| GET | `/api/session/{sid}/layers/aln2d/erosion` | 2D-ALN erosion polygons. |
| GET | `/api/session/{sid}/layers/aln2d/accretion` | 2D-ALN accretion polygons. |
| GET | `/api/session/{sid}/layers/aln2d/change` | Combined erosion/accretion diverging choropleth. |
| GET | `/api/session/{sid}/layers/aln2d/reaches` | Reach segments with 2D-ALN rates. |

## Tables & analytics

| Method | Path | Returns |
|---|---|---|
| GET | `/api/session/{sid}/table` | Per-transect rate rows (all methods). |
| GET | `/api/session/{sid}/diagnostics` | Cross-model fit stats (RMSE, R², BIC, MAE). |
| GET | `/api/session/{sid}/summary` | Dataset summary (% eroding, mean rates, extrema). |
| GET | `/api/session/{sid}/chart/{tid}` | Time-series traces + breaks + forecast for one transect. |
| GET | `/api/session/{sid}/scorecard` | Scorecard leaderboard + winner distribution. |
| GET | `/api/session/{sid}/aln2d/summary` | 2D-ALN morphodynamic budget rows. |
| GET | `/api/session/{sid}/aln2d/validation` | 2D-ALN vs 1D validation matrix. |
| GET | `/api/session/{sid}/aln2d/reaches` | Reach-level 2D-ALN vs 1D benchmark rows. |
| GET | `/api/session/{sid}/forecast-models` | Forecast models available for current results. |

## Exports

| Method | Path | File |
|---|---|---|
| GET | `/api/session/{sid}/export/csv` | `shift_transect_rates.csv` |
| GET | `/api/session/{sid}/export/intersections.csv` | `shift_intersections_raw.csv` |
| GET | `/api/session/{sid}/export/transects.geojson` | Full transect lines. |
| GET | `/api/session/{sid}/export/transects_rates.geojson` | Rate-styled transect envelope. |
| GET | `/api/session/{sid}/export/forecast.geojson` | Forecast shoreline. |
| GET | `/api/session/{sid}/export/bundle.zip` | Full GIS package — see [Export Artifacts](/docs/reference/export-artifacts). |

## System

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{status: "ok"}` |
