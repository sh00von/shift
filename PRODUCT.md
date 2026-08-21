# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Coastal geoscientists, coastal zone managers, geomorphologists, and GIS practitioners who need to analyze shoreline change rates, detect structural regime shifts, and make defensible coastal hazard assessments.

## Product Purpose

SHIFT is a statistical changepoint framework and interactive analysis workbench for coastal shoreline time series. It enables users to cast transects, compute standard coastal metrics, detect historical changepoints/regime shifts, perform robust outlier-resistant regressions, and generate forward shoreline position forecasts with quantified uncertainty.

## Positioning

A modern, browser-based alternative to legacy USGS DSAS workflows that pairs classic shoreline rate metrics (EPR, LRR, WLR, SCE, NSM) with automated statistical changepoint detection (Pelt, Bayesian regime shifts) and robust regressions (Theil-Sen, RANSAC), eliminating blind spots caused by assuming constant linear change over multi-decadal records.

## Operating Context

- Desktop browser workflows evaluating multi-temporal GIS shoreline shapefiles/GeoJSONs (historical surveys from 1990s to present).
- Interactive dual-pane layout: synchronized 2D GIS map view (Leaflet with satellite/topographic layers, transect lines, baseline, shoreline vectors, and choropleth rate mapping) alongside analytical inspector panels (transect time-series charts, regime breakpoint plots, attribute tables, and model diagnostics).
- High-frequency data inspection across dozens to hundreds of shore-perpendicular transects.

## Capabilities and Constraints

- **Input Ingestion**: Upload shoreline geometries with timestamps/dates and positional uncertainties (GeoJSON/Shapefile) and an offshore/onshore baseline.
- **Transect Generation**: Automated casting of orthogonal transects along baseline curves with configurable spacing and length.
- **Statistical Analysis Suite**:
  - Classic DSAS: End Point Rate (EPR), Linear Regression Rate (LRR), Weighted Linear Regression (WLR), Net Shoreline Movement (NSM), Shoreline Change Envelope (SCE).
  - Changepoint Detection: Ruptures (Pelt / BinSeg / KernelCPD) and Bayesian changepoint analysis with uncertainty intervals.
  - Robust Regression: Theil-Sen estimator and RANSAC for outlier resistance.
  - Forecasting: Extrapolation of recent regimes with prediction bounds.
- **Interactive Visualization**: Map canvas with choropleth transects, interactive time-series plots with Plotly, tabular data export (CSV/GeoJSON), and execution console logging.
- **Backend Architecture**: FastAPI service orchestrating GeoPandas, Shapely, PyMC, Ruptures, and Scikit-learn.
- **Frontend Architecture**: Next.js (App Router), React 19, TypeScript, Tailwind CSS v4, Zustand state store, Base UI / Shadcn.

## Brand Commitments

- **Name**: SHIFT (Geospatial Bayesian & Automated Changepoint framework).
- **Tone & Voice**: Scientific, precise, trustworthy, analytical, high-density scientific workbench aesthetic.
- **Visual Identity**: Clean dark/light scientific GIS theme with high data contrast, crisp cartographic symbology, and responsive interactive feedback.

## Evidence on Hand

- Sample shoreline surveys and baseline datasets (`sample_data/` and embedded demo dataset with 6 shoreline epochs from 1990–2023).
- Full Python statistical calculation engine (`shift/`).
- FastAPI backend endpoints with GeoJSON serialization and session management (`api/`).
- Interactive web frontend application (`frontend/`).

## Product Principles

1. **Scientific Rigor & Reproducibility**: Statistical metrics and changepoints must have clear mathematical foundations, parameter transparency, and explicit uncertainty quantification.
2. **Synchronized Geospatial Context**: Spatial geometry and temporal time-series charts must remain tightly linked—selecting a transect on the map immediately highlights its temporal history and statistics.
3. **Frictionless Exploration**: Instant feedback with sensible defaults, fast demo loading, responsive filtering, and seamless transition between map inspection and tabular analysis.
4. **Data Density without Clutter**: Maximize viewport utility for geospatial exploration while keeping diagnostic controls and tables organized in collapsible, dockable inspector panes.

## Accessibility & Inclusion

- Keyboard navigable tables, controls, and dialogs.
- High-contrast visual distinctions for transect choropleth color scales (colorblind-safe palettes for erosion vs. accretion).
- Clear numeric labels and metric units (e.g., m/yr, meters, dates) across all charts and tooltips.
