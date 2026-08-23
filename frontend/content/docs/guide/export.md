# Exporting Results

The **Export** dropdown produces GIS-ready data products. All exports are reprojected to
WGS84 (EPSG:4326).

## Options

| Export | File | Contents |
|---|---|---|
| **Full GIS Package (.ZIP)** | `bundle.zip` | Everything below plus a README and run config. |
| **Rate Metrics Summary (CSV)** | `shift_transect_rates.csv` | Per-transect rates for every method (EPR, LRR, WLR, Theil-Sen, RANSAC, Breakpoint). |
| **Clipped Rate Transects (GeoJSON)** | `shift_transects_rates_envelope.geojson` | Transects clipped to the shoreline envelope, with rate attributes. |
| **Full Orthogonal Transects (GeoJSON)** | `shift_transects_full.geojson` | Complete transect lines (no rates). |
| **Raw Intersections Series (CSV)** | `shift_intersections_raw.csv` | Every transect × shoreline intersection with date, position, and uncertainty. |
| **Forecast Shoreline (GeoJSON)** | `shift_forecast_shoreline.geojson` | Projected shoreline (shown only after a forecast is run). |

## The ZIP bundle

![Figure 12: GIS Export Package Bundle Structure](/docs/export_artifacts_structure.png)

The full package is the most complete deliverable. It contains a `README.txt` (session
summary + data dictionary), `session_config.json` (all run parameters), the CSVs and GeoJSONs
above, the input `shorelines.geojson` / `baseline.geojson`, the forecast line and uncertainty
cone (if generated), and — if the 2D-ALN engine was run — the erosion/accretion polygons,
reach rates (GeoJSON + CSV), the morphodynamic budget summary, and the statistical validation
matrix.

For the exact file list, see [Export Artifacts](/docs/reference/export-artifacts).

## Notes

- Exports require results — run the analysis first (the ZIP will still bundle inputs if only
  data is loaded).
- Downloads open in a new tab; your browser saves them to its default download location.
