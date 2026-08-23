# Breakpoint Detection

A single rate assumes the shoreline changed at a constant pace. Often it didn't — a storm,
an engineering intervention, or a regime shift changed the trend. `BreakpointMethod`
(`shift/stats/breakpoint.py`) fits a **piecewise** linear model and reports the change years
and the rate within each era.

![Structural Changepoint Detection vs Static Trend](/docs/breakpoint_regime.png)

## What it returns

- **`breakpoints`** — a list of detected breaks, each with its year, the rate before and
  after, and confidence intervals per segment.
- **`overall_rate`** — the rate of the most recent segment (the "current" trend), which is
  what forecasting uses.

## Algorithm

The method adapts to series length:

- **≤ 20 surveys** — an **exhaustive search** over all valid breakpoint configurations
  (respecting a minimum segment length), selecting the model that minimises **BIC**
  (Bayesian Information Criterion). BIC penalises extra breaks, so a break is only accepted
  when it genuinely improves the fit.
- **> 20 surveys** — **PELT** (Pruned Exact Linear Time) changepoint detection on the
  first-difference rate series, with an automatic penalty.

Each segment is fit by OLS; confidence intervals come from the t-distribution (90% by
default).

## Parameters (library-level)

| Parameter | Meaning | Default |
|---|---|---|
| `min_segment` | Minimum surveys per segment | 2 |
| `max_breaks` | Maximum breaks to search | 3 |
| `penalty` | Override the automatic BIC penalty | auto |

## Interpreting results

- The **inflection year** tells you *when* behaviour changed.
- The **post-break rate** is the trend that matters for the near future.
- In the Inspector chart, breaks appear as vertical dotted lines.

> **Guardrail:** in the [Scorecard](/docs/methods/scorecard), the breakpoint model is only
> eligible where the BIC gain clears the `Regime ΔBIC` threshold (default 6.0, "strong"
> Kass–Raftery evidence) **and** it beats plain LRR out-of-sample — preventing spurious
> breaks from winning.
