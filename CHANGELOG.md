# Changelog

All notable changes to the **SHIFT** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-23

### Added
- **2D-ALN Engine (2D Areal-to-Linear Normalization)**: Transect-free morphodynamic polygon budgeting computing exact erosion/accretion polygons ($\text{km}^2$), reach centerline normalization ($m/\text{yr}$), sediment mass balance, and cross-method consistency matrices.
- **Out-of-Sample Holdout Scorecard**: Robust backtesting validation engine (training on $1 \dots N-1$, predicting held-out survey $N$), evaluating **Holdout RMSE** and **Holdout MAE** per model across transects with domain guardrails ($\Delta\text{BIC} \ge 6.0$, $Z > 2.5$) and 5% parsimony tie-breaking.
- **Interactive Documentation Suite (`/docs`)**: Built-in 31-route static documentation center featuring technical deep-dives, scientific citations, API parameter references, and a complete suite of **16 high-resolution (300 DPI) minimal monochrome figures**.
- **Unit Test Suite**: Expanded tests covering 2D-ALN topology differencing and holdout scorecard validation (`17 passed`).

### Changed
- **Scorecard Protocol**: Streamlined from multi-fold LOOCV/rolling loops to direct out-of-sample holdout backtesting.
- **UI Table Layouts**: Added 2D-ALN Reach table, Morphodynamic Budget grid, and Holdout RMSE leaderboard to the bottom inspector dock.
- **Dependency Optimization**: Cleaned legacy `app/` PySide6 desktop folder and removed unused extras from `pyproject.toml`.

## [0.2.0] - 2026-08-21

### Added
- **Official SHIFT Logo**: Multi-color Google-palette shoreline-change icon added as browser favicon, splash screen emblem, and top app bar brand mark.
- **Monochrome Design System**: Replaced blue-tinted accent palette with a premium high-contrast monochrome (black/charcoal/gray) design system across the entire UI.
- **Minimal Pre-loader**: Redesigned the app splash screen to an ultra-minimal white layout featuring the logo, a thin progress bar, and a sub-label cycling indicator.
- **Open-Source Repository**: Project pushed to GitHub (`sh00von/shift`) with full README, LICENSE, CONTRIBUTING, CHANGELOG, CITATION.cff, and `.gitignore`.
- **Demo Dataset Renamed**: Standardized sample data filenames to `demo_shorelines.geojson` and `demo_baseline.geojson`.
- **Generalized Scope**: Renamed project subtitle to include River Bank Dynamics alongside Shoreline analysis throughout all documentation.

### Changed
- **Version badges** in README updated to exact installed versions (Next.js 16.3, React 19.2, FastAPI 0.141).
- **Text contrast** globally improved for monochrome readability (slate-400/500 overrides).
- **`skills-lock.json`** added to `.gitignore`.

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
