# 2D-ALN Engine

The **2D-ALN** (2D Areal-to-Linear Normalization) engine is a second, independent workflow
that measures change as **areas** rather than along transects. It needs no baseline and no
transects — it works directly on the shoreline polygons.

![Figure 8: 2D-ALN Polygon Morphodynamics vs. 1D Transect Distortion](/docs/2d_aln_morphodynamics.png)

## When to use it

Use 2D-ALN when you care about **how much land was lost or gained** (a sediment budget), or
when transect casting is awkward (highly sinuous braided rivers, complex bank geometry). It
complements the transect pipeline; a session can hold results from both.

## Running it

Click **2D-ALN** in the ribbon (needs only shorelines loaded). The progress modal shows four
stages: ingest & CRS → topology mask → 2D Boolean differencing → reach normalization. When it
finishes, the bottom dock switches to the **2D-ALN Morphodynamics** tab and two map layers
appear: **2D-ALN Change (Mass)** and **2D-ALN Reach Migration Rates**.

## Parameters

Open the settings popover next to the button:

| Parameter | Meaning | Default |
|---|---|---|
| **Reach length (m)** | Alongshore segment length over which area is normalized to a linear rate. | 1000 |
| **Reach buffer (m)** | Buffer around each reach used to clip its erosion/accretion polygons. | 1000 |
| **Bank search mask buffer (m)** | Search buffer around the bank union that constrains where change polygons are kept (removes far-field noise). | 5000 |

## What you get

- **Morphodynamic budget summary** — for each consecutive epoch pair: eroded km², accreted
  km², span in years, and erosion/accretion/net rates in km²/yr.
- **Reach table** — per reach: net, erosion, and accretion rates in m/yr, alongside 1D DSAS
  benchmarks (EPR, LRR, Kalman) for the same reach.
- **Cross-method comparison matrix** — correlation, RMSE, and bias of the 2D-ALN rates versus
  each 1D method. Note this is a consistency *comparison*, not a validation against ground
  truth (the two approaches measure different quantities). See
  [2D-ALN Method](/docs/methods/2d-aln) for the caveat.

## The method in brief

For each pair of dated shorelines, SHIFT closes them into land polygons and takes the Boolean
difference to get **erosion** (land lost) and **accretion** (land gained) polygons. It then
normalizes area to a linear migration rate per reach:

```
v = (Area / reach_length) / time
```

This areal-to-linear step is the **change-polygon approach**. For the scientific background,
prior art, and how SHIFT's implementation differs, see
[2D-ALN Method & Lineage](/docs/methods/2d-aln).
