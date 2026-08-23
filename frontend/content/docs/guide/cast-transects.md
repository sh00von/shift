# Casting Transects

Transects are shore-perpendicular measurement lines cast at regular intervals along the
baseline. Every distance-based rate (EPR, LRR, WLR, and the robust methods) is measured
where these transects cross each shoreline. This follows the USGS DSAS methodology.

![1D Orthogonal Transect Casting](/docs/transect_casting.png)

## Running it

Click **Cast** in the ribbon (enabled once both shorelines and baseline are loaded). A
progress modal shows the job; when it finishes, an **Orthogonal transects** layer appears on
the map (blue lines) and the attribute table opens in the bottom dock (empty until you run
the analysis).

## Geometry parameters

Open the settings popover (the slider icon next to **Cast**) to tune the geometry:

| Parameter | Meaning | Default |
|---|---|---|
| **Spacing (m)** | Alongshore interval between transects. Smaller = denser sampling, more transects. | 250 |
| **Smoothing (m)** | Window over which the baseline heading is averaged before casting perpendicular. Larger = smoother, less jittery transect directions. | 4000 |
| **Length (m)** | How long each transect is. Must be long enough to cross every shoreline. | 8000 |
| **Cast direction** | Which side of the baseline to cast toward — **Left** or **Right** of the digitised baseline flow. SHIFT can auto-detect the dominant side, but you can force it. | Right |

## Presets

Three quick presets set spacing/smoothing/length together:

- **50 m** — dense sampling (50 / 1000 / 3000).
- **250 m** — balanced default (250 / 4000 / 8000).
- **1 km** — coarse, fast overview (1000 / 10000 / 20000).

## Tips

- If transects don't reach your shorelines, increase **Length**.
- If transects cross each other on a wiggly baseline, increase **Smoothing**.
- If rates come out with the wrong sign (erosion vs accretion flipped), check the **Cast
  direction**.

Once transects look right, continue to [Running Rate Analysis](/docs/guide/run-analysis).
