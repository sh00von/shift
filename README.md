<p align="center">
  <img src="docs/logo.png" alt="SHIFT Logo" width="100" style="border-radius: 22px;" />
</p>

# SHIFT: Shoreline Intelligence, Forecasting & Trends - An Open-Source System for Shoreline and River Bank Dynamics

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python Version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-16.3-black" alt="Next.js" /></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19.2-blue" alt="React" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.141-009688.svg" alt="FastAPI" /></a>
  <a href="https://doi.org/10.5281/zenodo.22046678"><img src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.22046678-blue.svg" alt="DOI" /></a>
</p>

**SHIFT** is a modern geospatial changepoint framework and interactive analysis workbench for coastal shoreline and river bank time-series. It is built as a web-native, open-source alternative to legacy GIS tools (like USGS DSAS), pairing classic shoreline/river bank change metrics with structural changepoint detection (regime shifts) and robust outlier-resistant regressions.

### 📸 Screenshots Gallery

| Multi-temporal Shoreline Surveys | Rate Choropleth Map |
| :---: | :---: |
| <img src="docs/screenshots/03_shorelines.png" alt="Multi-temporal Shorelines" /> | <img src="docs/screenshots/01_rate_choropleth.png" alt="Rate Choropleth Map" /> |
| *Loading historical shoreline vectors automatically color-coded by survey date.* | *Visualizing spatial erosion and accretion rates using DSAS-style color ramps.* |
| **Interactive Attribute Table** | **Orthogonal Transects & Inspector** |
| <img src="docs/screenshots/04_analysis.png" alt="Analysis Results" /> | <img src="docs/screenshots/02_transects.png" alt="Orthogonal Transects" /> |
| *Comprehensive datagrid featuring classic, robust, and changepoint statistics.* | *Selecting individual transects to view robust regression fits and time-series.* |

---

## 🌟 Key Features

* **Automated Transect Caster**: Cast shore-perpendicular orthogonal transects along baseline curves with custom spacing, smoothing windows, and reach lengths.
* **Unified Statistics Suite**:
  * **USGS DSAS Rates**: End Point Rate (EPR), Linear Regression Rate (LRR), Weighted Linear Regression (WLR), Net Shoreline Movement (NSM), Shoreline Change Envelope (SCE).
  * **Robust Regression**: Outlier-resistant rate estimation using Theil-Sen estimators and RANSAC.
  * **Regime Changepoint Detection**: Automated changepoint analysis (PELT/BIC) detecting structural shifts in coastal trends (erosion-to-accretion transitions).
* **2D-ALN Morphodynamics Engine**: Transect-free 2D areal-to-linear normalization measuring sediment budgets (eroded/accreted $\text{km}^2$), reach centerline velocities ($m/\text{yr}$), and cross-method consistency matrices.
* **Out-of-Sample Holdout Scorecard**: Empirical model evaluation protocol ($1 \dots N-1 \rightarrow N$) ranking methods by **Holdout RMSE** and **Holdout MAE** with domain guardrails ($\Delta\text{BIC} \ge 6.0$, $Z > 2.5$) and 5% parsimony tie-breaking.
* **Spacious GIS Workbench UI**: 
  * Responsive Leaflet map with satellite/topographic basemaps.
  * Full-screen interactive Field Mapping Modal with custom date format parsers and on-the-fly uncertainty column creation.
  * Interactive Transect Inspector showing fit lines, changepoint indicators, and raw timeline charts.
  * 5-Tab Bottom Inspector dock with instant sorting, filters, diagnostics, 2D-ALN budget, and real-time logs.
* **In-App Documentation (`/docs`)**: 31-route static documentation suite containing mathematical formulas, citations, and 16 minimal monochrome 300 DPI technical diagrams.
* **Comprehensive GIS Package Export**: 1-click download of a compiled `.ZIP` containing formatted CSV rate metrics, raw intersections, full and envelope-clipped rate transects (GeoJSON), forecast shapes, and runtime configs.

---

## 🏗️ System Architecture

SHIFT is designed with a detached client-server model:
* **Backend Engine (`shift/` + `api/`)**: Built in Python with **GeoPandas**, **Shapely**, **PyProj**, **Ruptures** (for Peltier changepoints), and **Scikit-Learn**. Exposed as a REST + WebSocket API via **FastAPI**.
* **Frontend Interface (`frontend/`)**: Built using **Next.js 15 (App Router)**, **React 19**, **TypeScript**, **Zustand** state store, and **Tailwind CSS**. Map rendering is handled natively through **Leaflet**.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.11+
* Node.js 18+ and `npm`

### 1. Run the Python Backend
```bash
# Clone the repository
git clone https://github.com/sh00von/shift.git
cd shift

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install the package in editable mode with development dependencies
pip install -e ".[dev]"

# Launch the FastAPI server
uvicorn api.main:app --port 8000 --reload
```

### 2. Run the Next.js Frontend
```bash
cd frontend

# Install Node modules
npm install

# Run the Next.js dev server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to access the SHIFT Workbench.

---

## 📈 Usage Workflow

1. **Load Data**: Open the top menu and load the embedded **Demo Dataset** or upload your shoreline survey GeoJSON and offshore/onshore baseline.
2. **Configure Fields**: Map the survey Date column, set the date format, and map/create the Uncertainty attribute.
3. **Generate Transects**: Set spacing, reach, and cast direction, then preview/cast the orthogonal transects.
4. **Run Analysis**: Choose which models to fit (DSAS, Robust, Breakpoint) and compute rate metrics.
5. **Rank Methods**: Run the out-of-sample holdout scorecard to evaluate models by Holdout RMSE and identify winning methods per coastal sector.
6. **2D-ALN Morphodynamics**: Compute 2D polygon erosion/accretion budgets and reach-normalized migration rates.
7. **Forecast & Export**: Project future shoreline trajectories with expanding uncertainty cones and export the complete **GIS Bundle (.ZIP)**.

---

## 🧪 Running Tests

Validate the statistical engine, 2D-ALN differencing, and holdout scorecard using `pytest`:
```bash
python -m pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎓 Citation

If you use SHIFT in your academic research or thesis, please cite it using:
```bibtex
@software{Shovon_SHIFT_2026,
  author  = {Md. Minaruzzaman Shovon},
  title   = {SHIFT: Shoreline Intelligence, Forecasting & Trends - An Open-Source System for Shoreline and River Bank Dynamics},
  version = {0.3.0},
  year    = {2026},
  doi     = {10.5281/zenodo.22046678},
  url     = {https://doi.org/10.5281/zenodo.22046678}
}
```
Alternatively, see the [CITATION.cff](CITATION.cff) file for full metadata details.
