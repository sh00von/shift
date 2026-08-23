# Architecture

SHIFT is a detached client–server application. There is no shared runtime: the frontend and
backend communicate only over REST + WebSocket.

![Figure 15: Detailed 3-Tier Layered Architecture & Subsystem Interaction](/docs/architecture_overview.png)

## Three layers

Each layer depends only on the one below it.

### 1. `shift/` — pure analysis library

The scientific core, with no web dependencies. Key subpackages:

- `geometry/caster.py` — casts orthogonal transects (`cast_transects`) and computes shoreline
  intersections (`intersect_shorelines`).
- `timeseries/builder.py` — `build_series` turns intersections into per-transect
  distance-vs-time `TransectSeries`.
- `stats/` — one class per method (`DSASMethod`, `TheilSenMethod`, `RansacMethod`,
  `BreakpointMethod`), each with `.fit(series)`.
- `forecast/extrapolate.py` — `forecast()` and `kalman_forecast()`.
- `aln2d/engine.py` — the area-based **2D-ALN** workflow (`ALN2DEngine`).
- `validation/scorecard.py` — `build_scorecard` cross-validation ranking.
- `io/loader.py`, `report/writer.py` — data loading and report output.
- `models.py` — the shared result dataclasses (see [Data Models](/docs/reference/data-models)).

### 2. `api/` — FastAPI wrapper (stateful, in-memory)

- `session.py` — the `Session` dataclass holds everything for one browser session (uploaded
  file paths, all UI params, and pipeline outputs). `store` is a process-global in-memory
  dict. **Sessions do not survive a server restart** — the frontend detects a lost session
  and transparently recreates one.
- `pipeline.py` — the only module that imports `shift`. Functions `preview_transects`,
  `run_analysis`, `run_aln2d`, `run_scorecard`, and `generate_forecast` take
  `(Session, progress_callback)` and mutate the session in place. Also holds `parse_dates`
  and the synthetic demo-data generators.
- `main.py` — all HTTP routes and the WebSocket endpoints. Long jobs run via `_run_job`,
  which executes a blocking pipeline function in a worker thread (`asyncio.to_thread`) and
  streams `progress`/`done`/`error` frames.
- `geojson.py` — converts session outputs to map-ready GeoJSON + choropleth styling.
- `serialize.py` — converts outputs to table rows, chart data, diagnostics, and 2D-ALN tables.

### 3. `frontend/` — Next.js App Router workbench

- `lib/store.ts` — a single Zustand store (session id, params, loaded layers, selected
  transect, layer visibility/opacity, UI state). Auto-recovers dropped sessions.
- `lib/api.ts` — the typed REST + WebSocket client.
- `components/shift/` — the UI (Leaflet map, ribbon, layer tree, inspectors).

## The job pattern

Long-running work (preview, analyze, aln2d, scorecard, forecast) is not a plain HTTP call. The
frontend opens a WebSocket; the backend runs the blocking pipeline function in a thread and
streams progress frames; the UI shows a staged progress modal. On completion the frontend
re-fetches the relevant layers and tables. See [WebSocket Jobs](/docs/reference/websockets).
