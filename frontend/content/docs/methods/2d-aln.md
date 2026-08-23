# 2D-ALN Method & Lineage

**2D-ALN** (2D Areal-to-Linear Normalization) measures shoreline/bank change from **areas**
rather than transects. It is implemented in `shift/aln2d/engine.py` (`ALN2DEngine`). This
page documents the algorithm and, importantly, situates it in the existing scientific
literature.

## The algorithm

![2D-ALN Morphodynamics vs 1D Transects](/docs/2d_aln_morphodynamics.png)

For a chronologically sorted set of dated shorelines:

1. **Ingest & project** — parse epochs, reproject to a metric UTM CRS.
2. **Close topology** — convert each open shoreline `LineString` into a closed land
   `Polygon` (against a shared baseline where needed to avoid spurious self-closing wedges).
3. **Boolean set differencing** — for each consecutive epoch pair, compute
   **erosion = land₁ \ land₂** (land lost) and **accretion = land₂ \ land₁** (land gained),
   clipped to a bank search mask. This yields an areal budget in km²/yr.
4. **Reach normalization** — segment the coast into fixed-length reaches and normalize the
   clipped areas to a **linear migration rate**:

   ```
   v = (Area / reach_length) / time     [m/yr]
   ```

5. **Cross-method comparison** — compare the reach rates against 1D DSAS methods (EPR, LRR,
   Kalman) cast off the same reference shore, producing a correlation/RMSE/bias matrix.

> **This is a comparison, not a validation.** The 2D-ALN reach rate (an area normalized over
> a reach) and a 1D transect rate (movement at a point) are *different physical quantities*,
> and the 1D methods are not ground truth. Agreement is reassuring and disagreement is
> diagnostic, but neither *validates* the other. Treat the matrix as a cross-method
> consistency check; true validation requires independent field/survey measurements.

See the [2D-ALN user guide](/docs/guide/2d-aln) for running it and its parameters.

## Is this method new? — Related work

The core of 2D-ALN is **not** a novel invention; it is a known family called the **Area-Based
Analysis (ABA)** or **"change polygon"** approach. Be precise about this when citing SHIFT.

- **Smith, M.J. & Cromley, R.G. (2012).** *Measuring Historical Coastal Change using GIS and
  the Change Polygon Approach.* **Transactions in GIS, 16(1), 3–15.**
  doi:10.1111/j.1467-9671.2011.01292.x — the foundational reference. It converts shorelines
  to land/water polygons and defines **average coastal change = net area ÷ shoreline
  length**, mathematically identical to the ALN normalization above. It also showed the
  polygon method is *more robust to parameter choice* than transect-from-baseline (no
  baseline-placement problem, no crossing transects).
- **"Area method compared with Transect method to measure shoreline movement."** *Geocarto
  International, 37(20) (2022).* doi:10.1080/10106049.2021.1926556 — a direct ABA-vs-TBA
  benchmark.
- **QSCAT — QGIS Shoreline Change Analysis Tool.** *Environmental Modelling & Software, 184,
  106263 (2025).* doi:10.1016/j.envsoft.2024.106263 — an existing open-source plugin that
  implements both transect-based and an area-based ("change polygon"-like) algorithm.

### What *is* defensible as SHIFT's contribution

Frame 2D-ALN honestly as an *implementation and extension* of the change-polygon method, not
a brand-new method:

1. **Automated, transect-free reach segmentation** producing a spatially continuous
   alongshore **velocity field** (most ABA studies measure length manually or per polygon).
2. **River-bank application** — the change-polygon literature is largely marine-coast; braided/
   meandering river-bank dynamics are less covered.
3. **Systems integration** — areal budget + reach velocity + a cross-method comparison against
   1D methods, inside one open web workbench alongside a transect pipeline.

> **Recommended framing:** *"an automated, transect-free implementation of the change-polygon /
> area-based approach, extended to continuous alongshore reach-velocity fields and applied to
> river-bank dynamics."* Cite Smith & Cromley (2012), the Geocarto (2022) comparison, and
> QSCAT (2025), and show that the reach normalization reduces to the change-polygon
> `net area / shoreline length` equation as a special case.
