# Forecast Models

Forecasting projects a transect's shoreline position forward and draws an uncertainty cone.
SHIFT offers two mechanisms, both in `shift/forecast/extrapolate.py`.

![Shoreline Forecast Extrapolation & Uncertainty Cone](/docs/forecast_cone.png)

## Linear extrapolation — `forecast()`

Takes the most relevant rate and extends it forward in a straight line. The rate is chosen by
priority from what's available:

```
breakpoint post-break rate → Theil-Sen → RANSAC → LRR → EPR → overall rate
```

The uncertainty band grows **linearly with time**, scaled by the per-segment confidence
interval. Simple, transparent, and appropriate when you trust the current trend to continue.

Parameters: `horizon_years` (projection window) and `ci` (confidence level, default 0.90).

## Kalman filter — `kalman_forecast()`

A DSAS-style recursive Bayesian filter (after **Long & Plant, 2012**) with a two-element
state:

```
x = [ position (m), rate (m/yr) ]
```

- **Filter phase:** each survey is assimilated as a noisy measurement of position, updating
  both the position and the rate estimate recursively.
- **Forecast phase:** prediction-only; the uncertainty band grows out of the propagated state
  covariance.

The Kalman cone is generally **more conservative** (wider, more principled) than linear
extrapolation because it accounts for the uncertainty in the rate itself.

## Choosing a model

| | Linear extrapolation | Kalman filter |
|---|---|---|
| Trend source | A single chosen rate | Recursively estimated |
| Uncertainty | Linear growth from CI | State-covariance growth |
| Character | Transparent, optimistic cone | Conservative, principled cone |

You select the driving model in the [Forecast](/docs/guide/forecast) popover. The confidence
level maps to a z-score internally (`_z_from_ci`).
