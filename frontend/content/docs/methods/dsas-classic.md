# DSAS Classic (EPR / LRR / WLR / NSM / SCE)

These are the standard USGS DSAS change statistics, computed per transect from its
distance-vs-time series. Implemented by `DSASMethod` in `shift/stats/classic.py`.

![Figure 13: Geometric Comparison of Classical USGS DSAS Metrics (EPR, LRR, NSM)](/docs/dsas_classic_methods.png)

Let each transect have shoreline positions $d_1 \dots d_n$ (metres from the baseline) observed at
times $t_1 \dots t_n$ (decimal years), with the newest survey last.

## SCE — Shoreline Change Envelope

The total spread of shoreline positions, regardless of direction or time:

```
SCE = max(dᵢ) − min(dᵢ)     [metres]
```

A pure magnitude of variability.

## NSM — Net Shoreline Movement

Net displacement between the oldest and newest survey:

```
NSM = dₙ − d₁     [metres]
```

Positive/negative depends on the cast direction convention.

## EPR — End Point Rate

NSM divided by the elapsed time — the simplest rate:

```
EPR = (dₙ − d₁) / (tₙ − t₁)     [m/yr]
```

Uses only the two endpoint surveys; ignores everything in between.

## LRR — Linear Regression Rate

The slope of an ordinary least-squares line fit through **all** surveys:

```
d = a + LRR · t
```

Reported with its **R²**. Uses all data but is sensitive to outliers.

SHIFT also computes a **95% confidence interval** on the LRR slope (from its standard error and
a Student-t critical value) and a **significance flag**: if the interval **includes zero**, the
rate is **not statistically distinguishable from stable**. This drives the **Trend** column in
the attribute table and the verdict strip in the Inspector — a rate like `−0.3 ± 1.2 m/yr` is
reported as *Stable*, not erosion. Always read the rate together with this interval rather than
the point value alone.

## WLR — Weighted Linear Regression Rate

Like LRR, but each survey is weighted by the inverse square of its positional uncertainty:

```
wᵢ = 1 / uncertaintyᵢ²
```

so more precise surveys pull the fit more. Reported with its weighted **R²**. This is why the
[uncertainty column](/docs/guide/field-mapping) matters.

> **Note:** if every survey has the **same** uncertainty (e.g. the default 10 m constant),
> the weights are all equal and **WLR is mathematically identical to LRR**. In that case the
> two columns will match exactly — WLR only diverges from LRR when you supply *per-survey*
> uncertainties that actually vary between surveys.

## When to use which

- **EPR** — quick, transparent, but noisy with irregular sampling.
- **LRR** — the standard trend when surveys are evenly reliable.
- **WLR** — when survey precision varies (e.g. mixed data sources).
- **NSM / SCE** — descriptive magnitudes, not rates.

For outlier-resistant alternatives see [Robust methods](/docs/methods/robust); to detect a
change in trend see [Breakpoint detection](/docs/methods/breakpoint).
