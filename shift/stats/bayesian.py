"""
Bayesian changepoint detection — secondary contribution.

Uses PyMC to model a single changepoint in the (year, distance) series,
returning P(break at t) and credible intervals on per-era rates.
Kept as a single-breakpoint model to keep inference tractable on short series.
"""
from __future__ import annotations

import numpy as np

from shift.models import Breakpoint, RateResult, TransectSeries
from shift.stats.base import BaseMethod


class BayesianMethod(BaseMethod):
    """
    Parameters
    ----------
    n_samples   MCMC draws (after tuning)
    tune        MCMC tuning steps
    chains      Number of chains
    """

    def __init__(
        self,
        n_samples: int = 1000,
        tune: int = 1000,
        chains: int = 2,
    ) -> None:
        self.n_samples = n_samples
        self.tune = tune
        self.chains = chains

    def fit(self, series: TransectSeries) -> RateResult:
        try:
            import pymc as pm
            import pytensor.tensor as pt
        except ImportError:
            raise ImportError("PyMC is required for BayesianMethod: pip install pymc")

        if len(series) < 4:
            from shift.stats.classic import ClassicMethod
            r = ClassicMethod().fit(series)
            r.method = "bayesian"
            return r

        years = np.array(series.years(), dtype=float)
        d = np.array(series.distances, dtype=float)
        n = len(years)

        with pm.Model() as model:
            # Uniform prior on changepoint index
            tau = pm.DiscreteUniform("tau", lower=1, upper=n - 2)

            rate1 = pm.Normal("rate1", mu=0, sigma=100)
            rate2 = pm.Normal("rate2", mu=0, sigma=100)
            intercept1 = pm.Normal("intercept1", mu=np.mean(d), sigma=200)
            intercept2 = pm.Normal("intercept2", mu=np.mean(d), sigma=200)
            sigma = pm.HalfNormal("sigma", sigma=50)

            idx = pt.arange(n)
            mu = pm.math.switch(idx < tau,
                                intercept1 + rate1 * (years - years[0]),
                                intercept2 + rate2 * (years - years[0]))

            obs = pm.Normal("obs", mu=mu, sigma=sigma, observed=d)

            trace = pm.sample(
                self.n_samples,
                tune=self.tune,
                chains=self.chains,
                progressbar=False,
                return_inferencedata=True,
            )

        tau_samples = trace.posterior["tau"].values.flatten()
        tau_mode = int(np.bincount(tau_samples.astype(int)).argmax())
        break_year = float(years[tau_mode])

        rate1_samples = trace.posterior["rate1"].values.flatten()
        rate2_samples = trace.posterior["rate2"].values.flatten()

        r1_mean = float(np.mean(rate1_samples))
        r2_mean = float(np.mean(rate2_samples))
        r1_ci = (float(np.percentile(rate1_samples, 5)),
                 float(np.percentile(rate1_samples, 95)))
        r2_ci = (float(np.percentile(rate2_samples, 5)),
                 float(np.percentile(rate2_samples, 95)))

        # P(break) — proxy: fraction of samples where rate1 and rate2 differ > 1 m/yr
        prob = float(np.mean(np.abs(rate2_samples - rate1_samples) > 1.0))

        bp = Breakpoint(
            year=break_year,
            rate_before=r1_mean,
            rate_after=r2_mean,
            ci_before=r1_ci,
            ci_after=r2_ci,
            probability=prob,
        )

        return RateResult(
            transect_id=series.transect_id,
            method="bayesian",
            breakpoints=[bp],
            overall_rate=r2_mean,
        )
