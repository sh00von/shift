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
    lrr_ci_low: float | None = None    # 95% CI lower bound of the LRR slope (m/yr)
    lrr_ci_high: float | None = None   # 95% CI upper bound of the LRR slope (m/yr)
    lrr_significant: bool | None = None  # True if the 95% CI excludes zero
    wlr: float | None = None    # Weighted Linear Regression (m/yr)

    # EKF analysis method (timeseries.py)
    ekf: float | None = None       # Extended Kalman Filter slope (m/yr)

    # Non-parametric robust stats
    sens: float | None = None          # Sen's slope (m/yr) — median of pairwise slopes
    mk_tau: float | None = None        # Mann-Kendall τ (−1 to +1)
    mk_p: float | None = None          # Mann-Kendall p-value

    # Fitted curve points for EKF chart display
    fitted_years: list[float] = field(default_factory=list)
    fitted_values: list[float] = field(default_factory=list)

    # Forecast (forecast module appends this)
    forecast_years: list[float] = field(default_factory=list)
    forecast_distances: list[float] = field(default_factory=list)
    forecast_lower: list[float] = field(default_factory=list)
    forecast_upper: list[float] = field(default_factory=list)



@dataclass
class MorphodynamicBudget:
    """Areal mass change record between two chronological epochs."""
    from_epoch: str
    to_epoch: str
    span_years: float
    eroded_km2: float
    accreted_km2: float
    erosion_rate_km2_yr: float
    accretion_rate_km2_yr: float
    net_balance_km2_yr: float


@dataclass
class ReachRate:
    """2D-ALN reach rate and comparative 1D DSAS benchmark metrics."""
    reach_id: int
    length_m: float
    net_2d_m_yr: float
    ero_2d_m_yr: float
    acc_2d_m_yr: float
    dsas_epr_m_yr: float = 0.0
    dsas_lrr_m_yr: float = 0.0
    dsas_kf_m_yr: float = 0.0


@dataclass
class ALN2DValidationMetric:
    """Statistical metric comparing 2D-ALN ground truth to 1D DSAS models."""
    metric_name: str
    vs_lrr: str
    vs_epr: str
    vs_kf: str

