"""Base interfaces for category-specific research fetchers."""

from abc import ABC, abstractmethod

from kal_predict.models import MarketSnapshot, ResearchSnapshot, Signal


class BaseResearchFetcher(ABC):
    """Abstract interface for category research fetchers."""

    category_name: str
    min_edge_threshold: float

    @abstractmethod
    async def fetch(self, market: MarketSnapshot) -> ResearchSnapshot:
        """Fetch or derive research for a market."""
        raise NotImplementedError

    @abstractmethod
    def signals(self, research_snapshot: ResearchSnapshot) -> list[Signal]:
        """Return directional signals from a research snapshot."""
        raise NotImplementedError

