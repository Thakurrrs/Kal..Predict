"""Tests for deterministic market category routing."""

import pytest

from kal_predict.models import MarketSnapshot
from kal_predict.research.router import MarketCategoryRouter, ParserStatus


def make_market(title: str, ticker: str = "TEST-MARKET") -> MarketSnapshot:
    return MarketSnapshot(
        market_id=ticker,
        ticker=ticker,
        title=title,
        timestamp="2026-06-08T12:00:00Z",
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
        status="open",
    )


class TestMarketCategoryRouter:
    """Router assigns categories without inventing unsupported coverage."""

    @pytest.fixture
    def router(self) -> MarketCategoryRouter:
        return MarketCategoryRouter()

    def test_classifies_economics_market(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will CPI inflation be above 3.0% in June?"))

        assert result.category == "economics"
        assert result.reason == "keyword_match"
        assert result.enabled_for_paper is True

    def test_classifies_weather_market(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will New York City get rain tomorrow?"))

        assert result.category == "weather"
        assert result.reason == "keyword_match"
        assert result.enabled_for_paper is True

    def test_classifies_sports_market(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will Argentina win its World Cup match?"))

        assert result.category == "sports"
        assert result.reason == "known_disabled"
        assert result.enabled_for_paper is False
        # Broad sports stays observation-only, but soccer is the recognized slice.
        assert result.subcategory == "soccer"
        assert result.parser_status == ParserStatus.SUPPORTED

    def test_non_soccer_sports_is_unsupported_slice(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will the Lakers win their next NBA game?"))

        assert result.category == "sports"
        assert result.enabled_for_paper is False
        assert result.subcategory is None
        assert result.parser_status == ParserStatus.UNSUPPORTED

    def test_enabled_category_is_supported_status(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will CPI inflation be above 3.0% in June?"))

        assert result.parser_status == ParserStatus.SUPPORTED

    def test_ambiguous_market_has_ambiguous_parser_status(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will Trump attend the World Cup final?"))

        assert result.parser_status == ParserStatus.AMBIGUOUS

    def test_empty_title_has_unsafe_parser_status(self, router: MarketCategoryRouter):
        result = router.classify(make_market(""))

        assert result.parser_status == ParserStatus.UNSAFE

    def test_classifies_politics_market(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will the Senate pass the bill?"))

        assert result.category == "politics"
        assert result.reason == "known_disabled"
        assert result.enabled_for_paper is False

    def test_empty_title_is_unknown_missing_title(self, router: MarketCategoryRouter):
        result = router.classify(make_market(""))

        assert result.category == "unknown"
        assert result.reason == "unknown_missing_title"
        assert result.enabled_for_paper is False

    def test_ambiguous_sports_politics_market_is_unknown(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will Trump attend the World Cup final?"))

        assert result.category == "unknown"
        assert result.reason == "unknown_ambiguous"
        assert set(result.matched_categories) == {"sports", "politics"}
        assert result.enabled_for_paper is False

    def test_ambiguous_economics_politics_market_is_unknown(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will Fed cut rates before the election?"))

        assert result.category == "unknown"
        assert result.reason == "unknown_ambiguous"
        assert set(result.matched_categories) == {"economics", "politics"}

    def test_ambiguous_weather_politics_market_is_unknown(self, router: MarketCategoryRouter):
        result = router.classify(make_market("Will NYC get rain on election day?"))

        assert result.category == "unknown"
        assert result.reason == "unknown_ambiguous"
        assert set(result.matched_categories) == {"politics", "weather"}

    def test_disabled_category_returns_known_disabled(self):
        router = MarketCategoryRouter(enabled_paper_categories={"weather"})

        result = router.classify(make_market("Will CPI inflation be above 3.0% in June?"))

        assert result.category == "economics"
        assert result.reason == "known_disabled"
        assert result.enabled_for_paper is False
