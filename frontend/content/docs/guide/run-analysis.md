# Running Rate Analysis

The **Calculate** button runs the full 1D rate pipeline: it intersects transects with every
shoreline, builds a distance-vs-time series per transect, and fits every enabled statistical
method.

## Choosing methods

Open the settings popover next to **Calculate** to toggle which models run:

| Toggle | Method | Notes |
|---|---|---|
| **USGS DSAS (EPR, LRR, WLR)** | Classic endpoint & regression rates | See [DSAS Classic](/docs/methods/dsas-classic) |
| **Theil-Sen Estimator** | Robust median-of-slopes | Resistant to outlier surveys |
| **RANSAC Regressor** | Random sample consensus | Rejects digitisation errors |
| **Breakpoint Detection** | Piecewise regime shifts (PELT/BIC) | Detects trend changes |

You can also set the **Default Uncertainty (m)** here — the fallback positional error used
when no per-survey uncertainty column is mapped.

## Running

Click **Calculate**. A progress modal shows a five-stage stepper:

1. **Ingest** — load and reproject shorelines/baseline.
2. **Transects** — cast transects (if not already current).
3. **Intersect** — compute transect × shoreline intersections.
4. **Models** — fit each enabled method per transect.
5. **Forecast** — prepare available forecast models.

The **Console** tab streams live messages throughout.

## Results

![Figure 6: Rate Calculation Pipeline & Choropleth Classification](/docs/rate_analysis_workflow.png)

When the run completes:

- A **Rate choropleth** layer appears, colouring transects by rate (LRR by default). Change
  the styling metric and colour ramp from the Layers panel — see
  [Map & Layers](/docs/guide/map-and-layers).
- The **Attribute table**, **Diagnostics**, and (after ranking) **Scorecard** tabs populate
  in the bottom dock — see [Bottom Inspector](/docs/guide/bottom-inspector).
- Clicking any transect opens its per-transect chart and metrics — see
  [Inspecting Transects](/docs/guide/inspect-transects).

Next steps: [rank the methods](/docs/guide/rank-methods) to get a recommendation, or
[forecast](/docs/guide/forecast) forward.
