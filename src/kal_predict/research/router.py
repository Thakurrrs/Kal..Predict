"""Deterministic Kalshi market category router."""

import re

from pydantic import BaseModel, Field

from kal_predict.models import MarketSnapshot


KEYWORD_MAP: dict[str, tuple[str, ...]] = {
    "economics": (
        "cpi",
        "inflation",
        "gdp",
        "unemployment",
        "fed",
        "federal reserve",
        "interest rate",
        "rates",
        "payroll",
        "jobs",
        "recession",
        "pce",
        "retail sales",
        "housing",
        "mortgage",
    ),
    "weather": (
        "temperature",
        "rain",
        "snow",
        "hurricane",
        "tornado",
        "flood",
        "drought",
        "storm",
        "forecast",
        "degrees",
        "inches",
        "precipitation",
    ),
    "sports": (
        "world cup",
        "nfl",
        "nba",
        "mlb",
        "nhl",
        "soccer",
        "football",
        "basketball",
        "baseball",
        "tennis",
        "golf",
        "match",
        "game",
        "championship",
        "playoff",
        "score",
        "win",
        "league",
    ),
    "politics": (
        "election",
        "president",
        "trump",
        "biden",
        "senate",
        "congress",
        "vote",
        "poll",
        "approval",
        "bill",
        "law",
        "supreme court",
        "governor",
        "mayor",
        "candidate",
        "primary",
        "debate",
    ),
}


class CategoryClassification(BaseModel):
    """Market category classification result."""

    category: str
    reason: str
    matched_categories: list[str] = Field(default_factory=list)
    enabled_for_paper: bool = False


class MarketCategoryRouter:
    """Classify markets into conservative research categories."""

    def __init__(self, enabled_paper_categories: set[str] | None = None) -> None:
        self.enabled_paper_categories = enabled_paper_categories or {"economics", "weather"}

    def _keyword_matches(self, title: str, keyword: str) -> bool:
        escaped = re.escape(keyword.lower())
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", title) is not None

    def classify(self, market: MarketSnapshot) -> CategoryClassification:
        """Classify a market title using deterministic keyword rules."""
        title = market.title.strip().lower()
        if not title:
            return CategoryClassification(
                category="unknown",
                reason="unknown_missing_title",
                matched_categories=[],
                enabled_for_paper=False,
            )

        matched = [
            category
            for category, keywords in KEYWORD_MAP.items()
            if any(self._keyword_matches(title, keyword) for keyword in keywords)
        ]
        matched = sorted(matched)

        if not matched:
            return CategoryClassification(
                category="unknown",
                reason="unknown_no_match",
                matched_categories=[],
                enabled_for_paper=False,
            )

        if len(matched) > 1:
            return CategoryClassification(
                category="unknown",
                reason="unknown_ambiguous",
                matched_categories=matched,
                enabled_for_paper=False,
            )

        category = matched[0]
        enabled = category in self.enabled_paper_categories
        return CategoryClassification(
            category=category,
            reason="keyword_match" if enabled else "known_disabled",
            matched_categories=matched,
            enabled_for_paper=enabled,
        )
