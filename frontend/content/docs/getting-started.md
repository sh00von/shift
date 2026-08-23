# Installation & First Run

SHIFT has two processes: the Python/FastAPI **backend** (analysis engine + API) and the
Next.js **frontend** (this workbench). Run both during development.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Git

## 1. Backend

From the repository root (`GeoBAC`):

```bash
pip install -e ".[dev]"
uvicorn api.main:app --port 8000 --reload
```

This installs the `shift` package plus development extras (pytest) and
starts the API on `http://localhost:8000`. Leave it running.

To run the test suite:

```bash
python -m pytest                       # all tests
python -m pytest tests/test_aln2d.py   # a single file
```

## 2. Frontend

From `frontend/`:

```bash
npm install
npm run dev      # Next.js dev server on http://localhost:3000
```

Open `http://localhost:3000`. The frontend expects the backend at
`http://localhost:8000` by default. To point it elsewhere, set
`NEXT_PUBLIC_API_BASE` in a `.env.local` file:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Other scripts:

```bash
npm run build    # production build
npm run start    # serve the production build
npm run lint     # eslint
```

## 3. First analysis (demo data)

![Figure 3: SHIFT Workbench Ribbon & Workflow Pipeline](/docs/ui_ribbon_overview.png)

1. In the top ribbon, click **Add data → Load demo dataset**. SHIFT loads six synthetic
   shoreline surveys (1990–2023) plus a baseline.
2. Click **Cast** to generate orthogonal transects across the shoreline envelope.
3. Click **Calculate** to compute change rates across all enabled models (EPR, LRR, WLR, Theil-Sen, RANSAC, Breakpoint).
4. Click a transect on the map to inspect its rates and time series in the right-hand panel.
5. Optionally click **Rank Methods**, **Forecast**, and **2D-ALN**, then **Export**.

That is the full pipeline. The rest of the [User Guide](/docs/guide/upload-data) covers each
step in depth.

> **Session note:** sessions live in the backend's memory and do **not** survive a server
> restart. If you restart `uvicorn`, the frontend detects the lost session and transparently
> creates a new one — you'll just need to reload your data.
