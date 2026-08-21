# Contributing to SHIFT

Thank you for your interest in contributing to **SHIFT (Shoreline Intelligence, Forecasting & Trends)**! Contributions from the coastal science, GIS, and software engineering communities are highly welcome.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)

## How Can I Contribute?

### Reporting Bugs
If you find a bug or unexpected behavior:
1. Search the existing Issues to check if it has already been reported.
2. If not, open a new Issue. Describe the bug, provide steps to reproduce, and attach sample datasets (or coordinate files) if applicable.

### Suggesting Enhancements & New Models
Coastal shoreline models are continually evolving. If you want to add a new rate calculation metric or machine learning model:
1. Open an Issue outlining the mathematical formulation and library dependencies.
2. Implement your rate method by extending the `BaseMethod` class in [`shift/stats/base.py`](file:///d:/thesis-work/GeoBAC/shift/stats/base.py).

---

## Development Setup

### 1. Backend Setup (Python + FastAPI)
Ensure you have Python 3.11+ installed. We recommend using a virtual environment:
```bash
# Clone the repository
git clone https://github.com/sh00von/shift.git
cd shift

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install editable package with dev & app dependencies
pip install -e ".[dev,app]"
```

Run the backend development server:
```bash
uvicorn api.main:app --port 8000 --reload
```

### 2. Frontend Setup (Next.js + TailwindCSS + Leaflet)
Ensure you have Node.js 18+ and `npm` installed:
```bash
cd frontend
npm install
npm run dev
```

---

## Project Architecture
- `shift/`: The core statistical calculation library.
  - `geometry/`: Orthogonal transect casting, baseline reach intersections.
  - `stats/`: Rate models (USGS DSAS, Robust Regressions, Changepoints, ML models).
  - `forecast/`: Extrapolation, projection horizons, and uncertainty cone computation.
- `api/`: FastAPI endpoints, serialization schemas, and WebSocket progress handlers.
- `frontend/`: Single Page Application (Next.js App Router).
- `tests/`: Automated pytest suites validating stats fitting pipelines.

---

## Coding Guidelines
- **Python**: Follow PEP 8 style guide. Keep spatial calculations vectorised using `geopandas` and `shapely`. Always write unit tests in `tests/` for new estimators.
- **Frontend**: Use TypeScript and React server/client components. Keep styling clean using vanilla CSS variables or utility classes. Do not hardcode z-indexes. Use the layers system provided in `lib/store.ts`.

## Testing
Always run backend tests before submitting a pull request:
```bash
python -m pytest
```
Ensure the frontend builds without TypeScript or compilation errors:
```bash
cd frontend
npm run build
```
