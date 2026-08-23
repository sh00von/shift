# Loading Data

Everything starts from the **Add data** menu in the top ribbon. You have four ways to get
layers into a session.

## Load demo dataset

**Add data → Load demo dataset.** Generates six synthetic shoreline surveys (1990–2023)
along a sinuous, progressively eroding coastline, plus a matching baseline. The shorelines
appear on the map (colour-coded by date) and in the Layers panel. This is the fastest way to
try the full pipeline.

## Upload shorelines

**Add data → Upload shorelines…** opens a file picker (`.geojson`/`.json` only). After
upload, SHIFT:

1. Parses the file and reports the feature count and columns.
2. Auto-detects likely **date** and **uncertainty** columns.
3. Opens the [Field Mapping](/docs/guide/field-mapping) dialog so you can confirm the date
   column, date format, and uncertainty handling.

![Figure 4: Field Mapping & Date Parser Configuration](/docs/upload_field_mapping.png)

## Upload baseline

**Add data → Upload baseline…** uploads a single reference `LineString`. Transects are cast
perpendicular to this line.

## Generate an auto-baseline

If you have shorelines but no baseline, SHIFT can synthesise one by unioning your shorelines,
buffering seaward by the session's `buffer_distance`, and extracting the boundary. This gives
a baseline roughly parallel to the coast to cast from.

![Figure 5: User-Supplied vs. Auto-Generated Baseline Envelope](/docs/auto_baseline_concept.png)

## After loading

- Loaded layers show up in the **Layers** panel on the left (see
  [Map & Layers](/docs/guide/map-and-layers)).
- The ribbon enables the next actions: once both shorelines **and** baseline are present, the
  **Cast** and **Calculate** buttons unlock. (The 2D-ALN engine needs only shorelines.)
- The **Console** tab (bottom dock) logs every load with feature counts.

> **Reset:** the circular reset icon on the right of the ribbon clears the whole session —
> uploads, parameters, and results.
