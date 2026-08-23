# Map & Layers

The centre of the workbench is a Leaflet map; the left panel is a QGIS-style **Layers** tree
that controls what's drawn and how.

## The map

- **Basemaps:** switch between OpenStreetMap, Esri World Imagery, and Carto Light (basemap
  selector in the Layers footer).
- **Controls:** zoom to full extent, zoom to the selected transect, and clear selection
  (top-right of the map).
- **Legend:** when a choropleth is active, a gradient legend shows the rate range and unit.
- **Interaction:** click a transect to select it; hover any feature for a tooltip (survey
  date, transect number, or rate).
- The **Status bar** (bottom) shows live cursor coordinates, zoom level, and CRS
  (EPSG:4326).

## The Layers panel

Layers are grouped into a draggable tree:

- **Method Comparison** — Best Method (per-transect winner).
- **Transects & Rates** — Forecast projection, Rate choropleth, Orthogonal transects.
- **Inputs** — Shoreline surveys, Baseline reference.
- **2D-ALN** — Reach Migration Rates, Change (Mass).

### Per-layer controls

- **Checkbox** — toggle visibility.
- **Expand arrow** — reveal legend, styling, and the opacity slider (10–100%).
- **Drag handle** — reorder draw order within a group.
- **Right-click** — zoom to layer extent, open its attribute table, or move to top/bottom.

Toolbar buttons show all / hide all layers and reset the layer order.

## Symbology

Expand a layer to restyle it:

- **Shoreline surveys** — choose the date colour **palette** (Turbo, Viridis, Plasma, Magma,
  Cividis, Cool, Spring). Also links to edit date/uncertainty fields.
- **Rate choropleth** — choose the **Style by metric** (LRR, EPR, Theil-Sen, RANSAC,
  Post-break rate, Break year, BIC gain) and the **Colour ramp** (Red-Yellow-Green,
  Turbo, Viridis, Coolwarm, Magma). The choropleth re-fetches and re-renders live.
- **2D-ALN layers** — diverging erosion↔accretion gradient with the rate range.
- **Best Method** — categorical legend listing each method, its colour, and transect count.

## Panels

The Status bar's right side toggles the three docks: left **Layers**, bottom **Inspector
dock**, and right **Transect Inspector**. All are resizable.
