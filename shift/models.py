"""Shared data model — all modules import from here."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class TransectSeries:
    """Per-transect (date, distance, uncertainty) time series."""
    transect_id: int
    dates: list[date]
    distances: list[float]        # metres from baseline (negative = landward)
    uncertainties: list[float]    # positional uncertainty per shoreline (metres)

    def __len__(self) -> int:
        return len(self.dates)

    def years(self) -> list[float]:
        """Decimal years for regression."""
        ref = self.dates[0].year
        return [d.year + (d.timetuple().tm_yday - 1) / 365.25 for d in self.dates]


@dataclass
class Breakpoint:
    """A detected regime-shift point."""
    year: float
    rate_before: float    # m/yr
    rate_after: float     # m/yr
    ci_before: tuple[float, float] = (0.0, 0.0)
    ci_after: tuple[float, float] = (0.0, 0.0)
    probability: float = 1.0      # used by Bayesian method


@dataclass
class RateResult:
    """
    Output of any stats method for one transect.
    Classic fields are always populated; method-specific fields default to None.
    """
    transect_id: int
    method: str

    # Classic DSAS metrics (always populated by classic.py; others may leave None)
    sce: float | None = None    # Shoreline Change Envelope (m)
    nsm: float | None = None    # Net Shoreline Movement (m)
    epr: float | None = None    # End Point Rate (m/yr)
    lrr: float | None = None    # Linear Regression Rate (m/yr)
    lrr_r2: float | None = None
    wlr: float | None = None    # Weighted Linear Regression (m/yr)
    wlr_r2: float | None = None

    # Changepoint results (breakpoint.py + bayesian.py)
    breakpoints: list[Breakpoint] = field(default_factory=list)
    overall_rate: float | None = None   # rate of final segment (most recent era)

    # Robust methods (robust.py) — outlier-resistant regression
    theilsen: float | None = None
    theilsen_r2: float | None = None
    ransac: float | None = None
    ransac_outliers: int | None = None

    # ML benchmark (rf.py) — prediction at held-out year
    rf_prediction: float | None = None
    rf_rmse: float | None = None

    # Forecast (forecast module appends this)


    forecast_years: list[float] = field(default_factory=list)
    forecast_distances: list[float] = field(default_factory=list)
    forecast_lower: list[float] = field(default_factory=list)
    forecast_upper: list[float] = field(default_factory=list)
