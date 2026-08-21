# Changelog

All notable changes to the **SHIFT** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-21

### Added
- **Core Geoprocessing Engine**: Orthogonal transect casting, baseline intersections, smoothing window algorithms.
- **Coastal Rate Estimators**:
  - USGS DSAS classical metrics (`EPR`, `LRR`, `WLR`, `NSM`, `SCE`).
  - Robust Median estimators (`Theil-Sen Robust`).
  - Resilient Consensus estimators (`RANSAC`).
  - Changepoint regime-shift models (`Pelt` post-break rate, break year).
  - Machine Learning non-linear benchmarks (`Random Forest`).
- **Interactive UI Workbench**:
  - Real-time Leaflet map renderer.
  - Spacious fullscreen Field Mapping workbench.
  - Interactive Transect Inspector (visualizing regression fits, survey dates, and changepoints).
  - Real-time progress bars and log drawer.
- **Export GIS Package**:
  - 1-click ZIP package creator assembling rate CSVs, raw intersections, full and envelope-clipped rate transect GeoJSONs, forecast layers, and metadata configuration.
- **Open-source Guidelines**: Initialized Git, `.gitignore`, `CONTRIBUTING.md`, `LICENSE`, and `CITATION.cff`.
