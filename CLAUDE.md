# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SHIFT** (Shoreline Intelligence, Forecasting & Trends) is a geospatial changepoint framework and web workbench for coastal shoreline and river-bank change analysis — a web-native open-source alternative to USGS DSAS. The repo root directory is `GeoBAC`, but the Python package and product are named `shift`.

The system is a **detached client-server app**: a Python analysis engine + FastAPI backend, and a Next.js frontend. There is no shared runtime — they talk over REST + WebSocket.

## Commands

### Backend (from repo root)
```bash
pip install -e ".[dev]"                    # install package + pytest
uvicorn api.main:app --port 8000 --reload  # run the API on :8000
python -m pytest                          # run all tests
python -m pytest tests/test_aln2d.py       # run a single test file
python -m pytest tests/test_classic.py::<func>  # run a single test
```

### Frontend (from `frontend/`)
```bash
npm install
npm run dev      # Next.js dev server on :3000
npm run build
npm run lint     # eslint
```

The frontend expects the backend at `http://localhost:8000` (see `frontend/lib/api.ts`).

## Architecture

Three layers, each depending only on the one below it:

### 1. `shift/` — pure analysis library (no web deps)
The scientific core. Key subpackages:
- `geometry/caster.py` — casts shore-perpendicular orthogonal transects from a baseline (`cast_transects`) and computes shoreline intersections (`intersect_shorelines`).
- `timeseries/builder.py` — `build_series` turns intersections into per-transect distance-vs-time `Series` objects (the unit every stats method consumes).
- `stats/` — one class per method, all exported from `shift.stats.__init__`: `DSASMethod` (EPR/LRR/WLR/NSM/SCE), `TheilSenMethod` + `RansacMethod` (robust), `BreakpointMethod` (Pelt/ruptures regime detection). All classical/robust — there is intentionally **no ML method** (Random Forest and Bayesian were removed). Each exposes `.fit(series)` returning a `RateResult` (`shift/models.py`). `DSASMethod` also computes a **95% CI + significance flag** on the LRR slope (`lrr_ci_low/high`, `lrr_significant`) — the basis for the "Trend / Stable" classification.
- `forecast/extrapolate.py` — `forecast()` (linear extrapolation; uncertainty from the propagated slope standard error, not a fixed %) and `kalman_forecast()` (DSAS-style state-space filter). Both append forecast fields to a `RateResult`.
- `validation/scorecard.py` — `build_scorecard()`: out-of-sample method ranking via holdout hindcasting ($1 \dots N-1 \rightarrow N$), with guardrails (robust methods only count where outliers exist; Breakpoint only where ΔBIC clears a threshold and it beats LRR; ties break toward the simpler method). This is the **evaluation** layer, distinct from in-sample fit stats.
- `aln2d/engine.py` — **2D-ALN** (2D Areal-to-Linear Normalization): an alternate *area/polygon-based* morphodynamic workflow, separate from the transect pipeline. Produces erosion/accretion polygons, linear reach rates, budget summary, and a cross-method comparison matrix. `standalone_2d_aln.py` is a self-contained variant.
- `io/loader.py`, `report/writer.py` — data loading and report output.

### 2. `api/` — FastAPI wrapper (stateful, in-memory)
- `session.py` — `Session` dataclass holds *everything* for one browser session: temp-file paths for uploaded layers, all UI params (spacing, method toggles, forecast/2D-ALN settings), and pipeline outputs (`transects`, `series_list`, `results`, `aln2d_*`). `store` is a process-global in-memory dict — **sessions do not survive a server restart**; the frontend detects "Session not found" and transparently recreates one.
- `pipeline.py` — the only module that imports `shift`. Functions `preview_transects`, `run_analysis`, `run_aln2d`, `run_scorecard`, `generate_forecast` take `(Session, progress_callback)` and mutate the session in place. Also holds the robust `parse_dates` date parser and synthetic baseline/demo-data generators.
- `main.py` — all HTTP routes + 5 WebSocket endpoints (`/ws/preview`, `/ws/analyze`, `/ws/aln2d`, `/ws/scorecard`, `/ws/forecast`). Long jobs run via `_run_job`, which executes a blocking pipeline fn in a worker thread (`asyncio.to_thread`) and streams `progress`/`done`/`error` frames to the browser. `main.py` also builds all CSV/GeoJSON/ZIP export artifacts.
- `geojson.py` — converts session outputs to map-ready GeoJSON + choropleth styling (rate colour ramps). `serialize.py` — converts outputs to table rows (incl. the Trend/CI classification), chart data, diagnostics, scorecard, and 2D-ALN tables for the frontend.

### 3. `frontend/` — Next.js App Router GIS workbench
- `lib/store.ts` — single Zustand store: session id, params, loaded map layers, selected transect, layer visibility/opacity, ribbon/bottom-tab UI state. Auto-recovers dropped sessions.
- `lib/api.ts` — typed REST + WebSocket client.
- `components/shift/` — the UI. `MapCanvas`/`MapView` (Leaflet), `TopAppBar` (ribbon: Add data / Cast / Calculate / 2D-ALN / Rank Methods / Forecast / Export), `LayersTOC`, `BottomInspector` (table / diagnostics / scorecard / 2D-ALN / console tabs), `TransectInspector`, `FieldMappingModal`, `ProgressModal`, `ScorecardView`, `ALN2DView`. There is also an in-app `/docs` route (`app/docs/`, `components/docs/`, markdown under `content/docs/`).

## Key conventions & gotchas

- **CRS handling**: inputs are standardised to WGS84 (EPSG:4326) on I/O; analysis runs in a projected UTM CRS auto-picked via `estimate_utm_crs()`. Exports are reprojected back to 4326.
- **GeoJSON only**: shapefile uploads (`.shp`/.dbf/etc.) are explicitly rejected — the app standardises on `.geojson`/`.json`.
- **Windows file handling**: when writing GeoPandas output to a `NamedTemporaryFile`, close the handle *before* `to_file()` — Windows won't let GeoPandas write to an open file (see `auto_baseline` in `main.py`).
- **Two independent analysis pipelines**: the transect-based rate pipeline (`run_analysis`) and the polygon-based 2D-ALN pipeline (`run_aln2d`) are separate; a session can hold results from both.
- **Estimation vs evaluation (single source of truth)**: `run_analysis` computes rates + **R²** only (R² is a free byproduct of each fit and is stored on the `RateResult`). The Diagnostics view (`serialize.diagnostics`) **reuses that stored R²** and only computes the *error* metrics (RMSE/MAE/BIC) — and only once **Rank Methods has run** (`state.scorecard is not None`, exposed as `has_errors`). Out-of-sample metrics live solely in the Scorecard. Never recompute a method's R² downstream, and never compute error metrics eagerly during analysis.
- **Demo data**: `load_demo` prefers hard-coded local paths (`D:\thesis-work\shore-geojson\...`), then falls back to bundled `sample_data/`, then to synthetically generated data.
- **Adding a new stats method**: create the class in `shift/stats/`, export it from `shift/stats/__init__.py`, add its result fields to `shift/models.py`, wire a `run_*` toggle into `Session` + `ParamPatch` + `_params`, call `.fit()` in `pipeline.run_analysis`, surface it in `serialize.py`/`geojson.py` and the frontend, and (if it should be ranked) add it as a competitor in `validation/scorecard.py`'s `METHODS`/`_predict`. Removing a method means unwiring all of these — grep the whole repo for the result key (e.g. `"rf"`) to catch every consumer.
