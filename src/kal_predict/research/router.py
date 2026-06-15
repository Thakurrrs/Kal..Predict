"""Deterministic Kalshi market category router."""

import re
from enum import Enum

from pydantic import BaseModel, Field

from kal_predict.models import MarketSnapshot


class ParserStatus(str, Enum):
    """Deterministic parse outcome for an observed market.

    - SUPPORTED: classified into a known category with a usable subcategory.
    - UNSUPPORTED: known category, but no supported subcategory parser yet.
    - AMBIGUOUS: matched more than one category; cannot route safely.
    - UNSAFE: cannot classify at all (e.g. missing/empty title).
    """

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    UNSAFE = "unsafe"


# Soccer-specific tokens used to mark the enabled slice within broad sports.
SOCCER_KEYWORDS: tuple[str, ...] = (
    "world cup",
    "soccer",
    "premier league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "champions league",
    "mls",
)

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
    parser_status: ParserStatus = ParserStatus.UNSAFE
    subcategory: str | None = None


class MarketCategoryRouter:
    """Classify markets into conservative research categories."""

    def __init__(self, enabled_paper_categories: set[str] | None = None) -> None:
        self.enabled_paper_categories = enabled_paper_categories or {"economics", "weather"}

    def _keyword_matches(self, title: str, keyword: str) -> bool:
        escaped = re.escape(keyword.lower())
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", title) is not None

    def _detect_subcategory(self, category: str, title: str) -> str | None:
        """Identify a supported subcategory slice within a broad category.

        Currently only soccer is recognized inside the broad ``sports`` category;
        this is the roadmap's enabled sports slice while the rest of sports stays
        observation-only.
        """
        if category == "sports" and any(
            self._keyword_matches(title, kw) for kw in SOCCER_KEYWORDS
        ):
            return "soccer"
        return None

    def classify(self, market: MarketSnapshot) -> CategoryClassification:
        """Classify a market title using deterministic keyword rules."""
        title = market.title.strip().lower()
        if not title:
            return CategoryClassification(
                category="unknown",
                reason="unknown_missing_title",
                matched_categories=[],
                enabled_for_paper=False,
                parser_status=ParserStatus.UNSAFE,
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
                parser_status=ParserStatus.UNSAFE,
            )

        if len(matched) > 1:
            return CategoryClassification(
                category="unknown",
                reason="unknown_ambiguous",
                matched_categories=matched,
                enabled_for_paper=False,
                parser_status=ParserStatus.AMBIGUOUS,
            )

        category = matched[0]
        enabled = category in self.enabled_paper_categories
        subcategory = self._detect_subcategory(category, title)
        # A category is "supported" when paper is enabled for it, or when a
        # recognized subcategory slice exists (e.g. soccer within sports) that
        # the system can observe and parse even if paper trading stays off.
        parser_status = (
            ParserStatus.SUPPORTED
            if (enabled or subcategory is not None)
            else ParserStatus.UNSUPPORTED
        )
        return CategoryClassification(
            category=category,
            reason="keyword_match" if enabled else "known_disabled",
            matched_categories=matched,
            enabled_for_paper=enabled,
            parser_status=parser_status,
            subcategory=subcategory,
        )
