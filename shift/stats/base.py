"""Abstract base for all stats methods."""
from abc import ABC, abstractmethod
from shift.models import TransectSeries, RateResult


class BaseMethod(ABC):
    @abstractmethod
    def fit(self, series: TransectSeries) -> RateResult:
        """Fit the method to a transect series and return results."""
        ...
