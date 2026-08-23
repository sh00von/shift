# Inspecting Transects

After analysis you can drill into any single transect to see its full time series and every
method's rate side by side.

## Selecting a transect

- **Click** a transect on the map, or
- Click a row in the **Attribute table** (bottom dock), or
- Use the **Previous / Next** arrows in the Inspector header to step through transects in
  order.

The map highlights the selected transect and you can **Zoom to transect** to centre on it.

## The Inspector panel (right)

The right-hand **Inspector** shows two sections for the selected transect:

### Time-series chart

![Figure 7: Interactive Transect Time-Series & Multi-Model Fit Lines](/docs/transect_inspector_chart.png)

A chart of shoreline **distance (m) vs survey year**, overlaying:

- Observed shoreline intersections (points with positional error bars $\pm \sigma$).
- Fitted rate lines from each method (LRR, EPR, robust fits).
- Detected **regime-shift years** as vertical dotted lines (from breakpoint detection).
- The **forecast** projection and its confidence ribbon, if a forecast has been run.

### Metric cards

A grid of the key numbers for this transect, colour-coded by sign (red = erosion, green =
accretion):

- **Linear rate (LRR)** — m/yr
- **Endpoint rate (EPR)** — m/yr
- **Theil-Sen** robust rate — m/yr
- **RANSAC** robust rate — m/yr
- **Breakpoint post-break rate** — m/yr, with a regime count and the inflection year

A **View in Table** link jumps to this transect's row in the attribute table.

If no transect is selected, the panel prompts you to click one on the map.

## Where the numbers come from

Each metric maps to a method documented in the [Methods Reference](/docs/methods/dsas-classic).
For how the methods are compared and ranked, see [Ranking Methods](/docs/guide/rank-methods).
