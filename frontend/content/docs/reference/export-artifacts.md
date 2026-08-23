# Export Artifacts

This page lists every file SHIFT produces. Standalone exports come from the individual
`/export/*` routes; the full package bundles them. All geometry is WGS84 (EPSG:4326).

## Standalone exports

| File | Route | Contents |
|---|---|---|
| `shift_transect_rates.csv` | `/export/csv` | Per-transect rates for every method. |
| `shift_intersections_raw.csv` | `/export/intersections.csv` | Every transect × shoreline intersection (date, position, uncertainty). |
| `shift_transects_full.geojson` | `/export/transects.geojson` | Full-length transect lines. |
| `shift_transects_rates_envelope.geojson` | `/export/transects_rates.geojson` | Transects clipped to the shoreline envelope with rate attributes. |
| `shift_forecast_shoreline.geojson` | `/export/forecast.geojson` | Projected shoreline (after a forecast). |

## Full GIS package — `bundle.zip`

![Figure 16: Complete Multi-Tier Export Package File Structure](/docs/export_artifacts_structure.png)

`GET /api/session/{sid}/export/bundle.zip` assembles a complete deliverable. Contents
(2D-ALN and forecast files appear only if those steps were run):

1. `README.txt` — session summary + data dictionary.
2. `session_config.json` — all run parameters.
3. `shift_transect_rates.csv` — all-method rates.
4. `intersections_raw.csv` — survey records.
5. `transects_rates_envelope.geojson` — styled transects.
6. `transects_full.geojson` — full transect lines.
7. `baseline.geojson` — reference line.
8. `shorelines.geojson` — survey shorelines.
9. `forecast_shoreline.geojson` — forecast line *(if generated)*.
10. `forecast_uncertainty_cone.geojson` — confidence cone *(if generated)*.
11. `processed_erosion_polygons.geojson` — 2D-ALN erosion *(if run)*.
12. `processed_accretion_polygons.geojson` — 2D-ALN accretion *(if run)*.
13. `processed_linear_reach_rates.geojson` — 2D-ALN reaches *(if run)*.
14. `processed_linear_reach_rates.csv` — reach rate table *(if run)*.
15. `morphodynamic_budget_summary.csv` — 2D-ALN budget *(if run)*.
16. `statistical_validation_matrix.csv` — 2D-ALN validation *(if run)*.

See [Exporting Results](/docs/guide/export) for the UI workflow.
