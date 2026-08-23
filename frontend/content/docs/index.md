# SHIFT Documentation

**SHIFT** (Shoreline Intelligence, Forecasting & Trends) is a geospatial changepoint
framework and web workbench for coastal shoreline and river-bank change analysis — a
web-native, open-source alternative to USGS DSAS.

This documentation covers everything the application does, in two parts:

- A **User Guide** — task-by-task walkthroughs of the workbench (load data → cast
  transects → analyse → rank → forecast → export).
- A **Methods & Technical Reference** — the science behind every statistical method and a
  developer-facing reference of the REST/WebSocket API, parameters, and export artifacts.

## What SHIFT does

SHIFT measures how a shoreline or river bank has moved over time and projects where it is
heading. You supply a set of dated shoreline surveys (as GeoJSON) and a reference baseline;
SHIFT casts shore-perpendicular transects, computes change rates with several statistical
methods, cross-validates them to recommend the most trustworthy one, and can forecast the
future position with an uncertainty cone.

It also ships a second, independent workflow — the **2D-ALN** engine — that measures
erosion and accretion as *areas* (polygon differencing) rather than along transects.

## How it compares to DSAS

| Capability | USGS DSAS | SHIFT |
|---|---|---|
| Transect casting (EPR, LRR, WLR, NSM, SCE) | ✔ | ✔ |
| Robust regression (Theil-Sen, RANSAC) | ✖ | ✔ |
| Changepoint / regime-shift detection | ✖ | ✔ (PELT) |
| Cross-validated method ranking | ✖ | ✔ (Scorecard) |
| Area-based morphodynamics | ✖ | ✔ (2D-ALN) |
| Forecasting | Kalman (add-on) | ✔ (linear + Kalman) |
| Platform | ArcGIS desktop | Web (browser) |

## Architecture at a glance

![Figure 1: SHIFT 3-Tier System Architecture](/docs/architecture_overview.png)

SHIFT is a detached client–server app with three distinct architectural layers:

1. **`shift/`** — a pure Python scientific analysis library (no web dependencies).
2. **`api/`** — a FastAPI backend that wraps the engine, holds per-session state in memory, and
   streams real-time pipeline execution over WebSockets.
3. **`frontend/`** — a Next.js 15 GIS workbench with interactive Leaflet mapping, Zustand state management, and real-time inspector docks.

See [Architecture Reference](/docs/reference/architecture) for details.

## Quick tour

1. **[Install & run](/docs/getting-started)** the backend and frontend.
2. **[Load data](/docs/guide/upload-data)** — click *Add data → Load demo dataset* to get
   started instantly, or upload your own shorelines and baseline.
3. **[Cast transects](/docs/guide/cast-transects)** along the baseline.
4. **[Run the analysis](/docs/guide/run-analysis)** to compute rates.
5. **[Inspect](/docs/guide/inspect-transects)**, **[rank](/docs/guide/rank-methods)**,
   **[forecast](/docs/guide/forecast)**, and **[export](/docs/guide/export)**.
