"""Tests for conservative sports research fetcher."""

import pytest

from kal_predict.models import MarketSnapshot
from kal_predict.research.sports import SportsResearchFetcher


def make_market(title: str, ticker: str = "SPORTS-MARKET") -> MarketSnapshot:
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


@pytest.mark.asyncio
async def test_sports_fetcher_observes_world_cup_match_winner():
    fetcher = SportsResearchFetcher()

    snapshot = await fetcher.fetch(
        make_market("Will Argentina beat Brazil in their World Cup match?")
    )

    assert snapshot.category == "sports"
    assert snapshot.usable is True
    assert snapshot.skip_reason is None
    assert snapshot.metadata["market_type"] == "match_winner"
    assert snapshot.metadata["competition"] == "world cup"
    assert snapshot.metadata["paper_trading_enabled"] is False
    assert snapshot.metadata["team_a"] == "Argentina"
    assert snapshot.metadata["team_b"] == "Brazil"
    assert snapshot.signals[0].source == "sports_parser"


@pytest.mark.asyncio
async def test_sports_fetcher_skips_non_world_cup_market():
    fetcher = SportsResearchFetcher()

    snapshot = await fetcher.fetch(make_market("Will Argentina beat Brazil in a friendly?"))

    assert snapshot.usable is False
    assert snapshot.skip_reason == "unsupported_competition"
    assert snapshot.metadata["paper_trading_enabled"] is False


@pytest.mark.asyncio
async def test_sports_fetcher_skips_ambiguous_team_parse():
    fetcher = SportsResearchFetcher()

    snapshot = await fetcher.fetch(make_market("Will Argentina win its World Cup match?"))

    assert snapshot.usable is False
    assert snapshot.skip_reason == "ambiguous_teams"
    assert snapshot.signals == []


@pytest.mark.asyncio
async def test_sports_fetcher_skips_unsupported_market_type():
    fetcher = SportsResearchFetcher()

    snapshot = await fetcher.fetch(make_market("Will Argentina score 3 goals vs Brazil in the World Cup?"))

    assert snapshot.usable is False
    assert snapshot.skip_reason == "unsupported_market_type"
