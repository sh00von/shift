# Ranking Methods

With several rate methods available, which one should you trust? The **Rank Methods**
(Scorecard) job answers that empirically by evaluating every method against held-out
surveys and recommending a winner.

## Running it

Click **Rank Methods** in the ribbon (enabled after you've run the analysis). SHIFT scores
each method per transect using an out-of-sample holdout test ($1 \dots N-1 \rightarrow N$) and applies guardrails, then opens
the **Model Scorecard** tab in the bottom dock.

## How methods are scored

![Figure 9: Out-of-Sample Holdout Protocol & Scorecard Leaderboard](/docs/holdout_scorecard.png)

- **Holdout / Hindcast ($1 \dots N-1 \rightarrow N$)**: Fits the model strictly on historical surveys ($1$ to $N-1$) and forecasts the shoreline position at the latest survey year ($N$).
- **Prediction Error**: Computes the difference between the true measured position $y_N$ and predicted position $\hat{y}_N$.

A method's score per transect is its absolute holdout error $|\text{Error}|$ (lower is better).

## Guardrail thresholds

Set these in the popover next to the button:

| Threshold | Default | Effect |
|---|---|---|
| **Regime ΔBIC ≥** | 6.0 | Breakpoint only qualifies where the BIC gain clears this ("strong" evidence) **and** it beats LRR on holdout error. |
| **Outlier \|z\| >** | 2.5 | Theil-Sen / RANSAC only count where genuine outliers exist; on clean data LRR is preferred. |
| **Tie margin (%)** | 5.0 | Methods within this % of the best error are treated as tied; ties break toward the simpler method. |

These guardrails stop complex methods from "winning" by overfitting when a simpler model is
just as good.

## Reading the Scorecard

- **Headline recommendation** — the modal winning method across transects, in plain English.
- **Leaderboard** — every method with its Holdout RMSE, Holdout MAE, in-sample R², BIC, coverage,
  and win %.
- **Method distribution** — a bar chart of how many transects each method won.

A **Best Method** map layer also appears, colouring each transect by its per-transect winner.

For the full algorithm, see [Model Scorecard](/docs/methods/scorecard).

