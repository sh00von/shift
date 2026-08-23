# Forecasting

Once rates are computed, SHIFT can project the shoreline forward and draw an uncertainty
cone around the prediction.

## Running it

![Figure 10: Shoreline Forward Forecast & 95% Propagated Uncertainty Cone](/docs/forecast_cone.png)

Click **Forecast** in the ribbon (enabled after analysis). A **Forecast projection** layer
appears with two parts:

- a dashed line showing the projected shoreline at the target year, and
- a semi-transparent **ribbon** — the confidence interval band that widens with time based on propagated parameter standard error.

The Inspector chart for a selected transect also updates to show the forecast line and its
confidence band.

## Configuration

Open the popover next to the button:

| Setting | Meaning | Default |
|---|---|---|
| **Driving model** | Which rate drives the projection. Only models actually computed in your analysis are offered. | first available |
| **Horizon (yrs)** | How many years forward to project. | 10 |
| **Confidence (%)** | Confidence level for the uncertainty cone. | 90 |

### Driving models

The dropdown is populated from your results and typically includes:

- **Kalman Filter (DSAS)** — recursive state-space filter (position + rate); more
  conservative uncertainty growth.
- **Breakpoint (Post-break Rate)** — uses the most recent regime's rate, ignoring older
  trends.
- **Theil-Sen / RANSAC Robust Rate** — robust to outliers.
- **Linear Regression (LRR)** / **Endpoint Rate (EPR)** — classic DSAS rates.

For the maths behind linear extrapolation vs the Kalman filter, see
[Forecast Models](/docs/methods/forecast-models).

## Exporting the forecast

Once a forecast exists, **Export → Forecast Shoreline (GeoJSON)** saves the projected line
(and the cone is included in the full ZIP bundle). See [Exporting](/docs/guide/export).
