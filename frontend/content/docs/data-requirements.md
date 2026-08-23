# Data Requirements

SHIFT needs two inputs: a set of **dated shoreline surveys** and a **baseline** reference
line. Both are vector geometry supplied as GeoJSON.

## File format: GeoJSON only

Uploads must be `.geojson` or `.json`. **Shapefiles (`.shp`/`.dbf`/etc.) are explicitly
rejected** — the app standardises on GeoJSON. If you have a shapefile, convert it first
(e.g. with QGIS: *Export → Save Features As → GeoJSON*, or `ogr2ogr out.geojson in.shp`).

## Shorelines layer

- **Geometry:** one `LineString` (or `MultiLineString`) feature per survey — the digitised
  position of the shore/bank at a point in time.
- **Date attribute:** each feature must carry a survey date in some property. The column
  name and format are configured in [Field Mapping](/docs/guide/field-mapping). Supported
  forms include full dates (`DD/MM/YYYY`, `YYYY-MM-DD`, `MM/DD/YYYY`) and bare years.
- **Uncertainty attribute (optional):** a per-survey positional error in metres. If you
  don't have one, SHIFT applies a default (10 m) or you can create a constant column during
  field mapping. Uncertainty feeds the Weighted Linear Regression (WLR) and the forecast
  cone.

A transect must intersect at least **two** shorelines to yield a rate, so provide enough
temporal coverage.

## Baseline layer

- **Geometry:** a single reference `LineString` roughly parallel to the shore, sitting
  landward (or seaward) of all surveys. Transects are cast perpendicular to it.
- If you don't have a baseline, use **Add data → (auto-baseline)** to generate one by
  buffering your shorelines. See [Loading Data](/docs/guide/upload-data).

## Coordinate reference systems (CRS)

![Figure 2: Geographic (WGS84) to Projected Metric (UTM) Conversion](/docs/data_requirements_crs.png)

You don't need to reproject anything manually:

- Inputs are standardised to **WGS84 (EPSG:4326)** on load.
- Analysis automatically reprojects features to a **projected metric UTM CRS** (e.g. UTM Zone 46N) auto-estimated from dataset centroid coordinates so that all transect casts, orthogonal intersections, and polygon areas are computed in true Euclidean metres ($m$).
- All exports and map display layers are reprojected back to EPSG:4326.

## Interpreting precision

SHIFT reports rates to 2–3 decimals (e.g. `−1.234 m/yr`), but that is **display precision, not
accuracy**. If your shorelines carry ~10 m positional uncertainty, the *meaningful* precision of
a rate is far coarser. Always read a rate alongside its uncertainty: the regression methods
(LRR/WLR) expose a standard error, Breakpoint reports per-era confidence intervals, and the
forecast draws an explicit uncertainty cone. Do not over-interpret sub-decimetre-per-year
differences between methods when survey error is metres.

## Scope: coasts and river banks

The transect pipeline follows the USGS DSAS model, which assumes a **single-valued shore
sampled perpendicular to one baseline**. This fits open coasts and single river banks well.
For **meandering or braided rivers**, opposing banks, or channel cut-offs, the perpendicular-
transect assumption can break down (transects may cross the wrong bank or intersect a shoreline
more than once). In those settings prefer the [2D-ALN](/docs/methods/2d-aln) area-based
workflow, which needs no baseline or transects, and treat transect rates as a cross-check.

## The demo dataset

If you just want to explore, **Add data → Load demo dataset** generates a synthetic eroding
coastline (six surveys, 1990–2023) with a matching baseline — no files required.
