"""Tests for market data and evidence fixtures.

Validates that pre-recorded fixtures load correctly and conform to data contracts.
"""

import pytest

from kal_predict.fixtures import (
    get_settlement_outcome,
    load_evidence_items,
    load_market_snapshots,
)
from kal_predict.models import EvidenceItem, MarketSnapshot


class TestLoadMarketSnapshots:
    """Test market snapshot fixture loading."""

    def test_load_market_snapshots_returns_correct_count(self):
        """Verify exactly 4 snapshots load."""
        snapshots, _ = load_market_snapshots()
        assert len(snapshots) == 4

    def test_load_market_snapshots_returns_pydantic_models(self):
        """Verify snapshots are MarketSnapshot Pydantic models."""
        snapshots, _ = load_market_snapshots()
        for snapshot in snapshots:
            assert isinstance(snapshot, MarketSnapshot)

    def test_market_snapshots_in_chronological_order(self):
        """Verify snapshots are ordered by timestamp."""
        snapshots, _ = load_market_snapshots()
        timestamps = [s.timestamp for s in snapshots]
        assert timestamps == sorted(timestamps)

    def test_market_snapshots_have_correct_market_id(self):
        """Verify all snapshots are for the same market."""
        snapshots, _ = load_market_snapshots()
        market_ids = {s.market_id for s in snapshots}
        assert market_ids == {"WEATHER_CHICAGO_TEMP_75_20260424"}

    def test_market_snapshots_have_valid_prices(self):
        """Verify bid < ask for both YES and NO."""
        snapshots, _ = load_market_snapshots()
        for snapshot in snapshots:
            assert snapshot.yes_bid <= snapshot.yes_ask
            assert snapshot.no_bid <= snapshot.no_ask

    def test_market_snapshots_prices_in_valid_range(self):
        """Verify all prices are between 0 and 1."""
        snapshots, _ = load_market_snapshots()
        for snapshot in snapshots:
            assert 0 <= snapshot.yes_bid <= 1
            assert 0 <= snapshot.yes_ask <= 1
            assert 0 <= snapshot.no_bid <= 1
            assert 0 <= snapshot.no_ask <= 1

    def test_market_snapshots_yes_no_prices_sum_to_one(self):
        """Verify bid/ask pairs approximately sum to 1."""
        snapshots, _ = load_market_snapshots()
        for snapshot in snapshots:
            yes_mid = (snapshot.yes_bid + snapshot.yes_ask) / 2
            no_mid = (snapshot.no_bid + snapshot.no_ask) / 2
            # Prices should sum to approximately 1.0 (allowing for spread)
            assert abs((yes_mid + no_mid) - 1.0) < 0.05

    def test_market_snapshots_volume_increases(self):
        """Verify volume increases over time (market heating up)."""
        snapshots, _ = load_market_snapshots()
        volumes = [s.volume for s in snapshots]
        # Each snapshot should have >= volume of previous
        for i in range(1, len(volumes)):
            assert volumes[i] >= volumes[i - 1]

    def test_market_snapshots_yes_price_increases(self):
        """Verify YES price increases over time (market converging to outcome)."""
        snapshots, _ = load_market_snapshots()
        yes_mids = [(s.yes_bid + s.yes_ask) / 2 for s in snapshots]
        # YES mid-price should increase over time
        for i in range(1, len(yes_mids)):
            assert yes_mids[i] >= yes_mids[i - 1]

    def test_settlement_data_exists(self):
        """Verify settlement data is returned."""
        _, settlement_data = load_market_snapshots()
        assert settlement_data is not None
        assert len(settlement_data) > 0

    def test_settlement_data_has_correct_structure(self):
        """Verify settlement data has required fields."""
        _, settlement_data = load_market_snapshots()
        market_id = "WEATHER_CHICAGO_TEMP_75_20260424"
        assert market_id in settlement_data

        settlement = settlement_data[market_id]
        assert "actual_outcome" in settlement
        assert "settlement_price" in settlement
        assert "timestamp" in settlement

    def test_settlement_outcome_is_yes(self):
        """Verify market resolved to YES (outcome=1)."""
        _, settlement_data = load_market_snapshots()
        market_id = "WEATHER_CHICAGO_TEMP_75_20260424"
        assert settlement_data[market_id]["actual_outcome"] == 1

    def test_settlement_price_is_correct(self):
        """Verify settlement price matches outcome."""
        _, settlement_data = load_market_snapshots()
        market_id = "WEATHER_CHICAGO_TEMP_75_20260424"
        settlement = settlement_data[market_id]
        if settlement["actual_outcome"] == 1:
            assert settlement["settlement_price"] == 1.0
        else:
            assert settlement["settlement_price"] == 0.0


class TestLoadEvidenceItems:
    """Test evidence item fixture loading."""

    def test_load_evidence_items_returns_correct_count(self):
        """Verify exactly 3 evidence items load."""
        evidence_items = load_evidence_items()
        assert len(evidence_items) == 3

    def test_load_evidence_items_returns_pydantic_models(self):
        """Verify items are EvidenceItem Pydantic models."""
        evidence_items = load_evidence_items()
        for item in evidence_items:
            assert isinstance(item, EvidenceItem)

    def test_evidence_items_in_chronological_order(self):
        """Verify evidence items are ordered by retrieved_at."""
        evidence_items = load_evidence_items()
        timestamps = [item.retrieved_at for item in evidence_items]
        assert timestamps == sorted(timestamps)

    def test_evidence_items_have_valid_ids(self):
        """Verify evidence IDs are unique."""
        evidence_items = load_evidence_items()
        evidence_ids = [item.evidence_id for item in evidence_items]
        assert len(evidence_ids) == len(set(evidence_ids))

    def test_evidence_items_have_nws_source(self):
        """Verify all items are from NWS."""
        evidence_items = load_evidence_items()
        sources = {item.source for item in evidence_items}
        assert sources == {"NWS"}

    def test_evidence_items_have_valid_urls(self):
        """Verify all items have NWS API URLs."""
        evidence_items = load_evidence_items()
        for item in evidence_items:
            assert "api.weather.gov" in item.url
            assert "gridpoints" in item.url

    def test_evidence_items_confidence_in_valid_range(self):
        """Verify confidence_hint is between 0 and 1."""
        evidence_items = load_evidence_items()
        for item in evidence_items:
            assert 0 <= item.confidence_hint <= 1

    def test_evidence_items_reliability_in_valid_range(self):
        """Verify reliability_score is between 0 and 1."""
        evidence_items = load_evidence_items()
        for item in evidence_items:
            assert 0 <= item.reliability_score <= 1

    def test_evidence_confidence_increases_over_time(self):
        """Verify confidence increases as evidence accumulates."""
        evidence_items = load_evidence_items()
        confidences = [item.confidence_hint for item in evidence_items]
        # Confidence should increase over time as we approach settlement
        for i in range(1, len(confidences)):
            assert confidences[i] >= confidences[i - 1]

    def test_evidence_reliability_increases_over_time(self):
        """Verify reliability improves over time."""
        evidence_items = load_evidence_items()
        reliabilities = [item.reliability_score for item in evidence_items]
        # Reliability should increase over time (NWS improves as event approaches)
        for i in range(1, len(reliabilities)):
            assert reliabilities[i] >= reliabilities[i - 1]

    def test_evidence_claims_mention_chicago_temperature(self):
        """Verify claims are about Chicago temperature."""
        evidence_items = load_evidence_items()
        for item in evidence_items:
            # Should mention Chicago and temperature in claim
            assert any(keyword in item.claim for keyword in ["Chicago", "temp", "°F", "75"])

    def test_final_evidence_has_high_confidence(self):
        """Verify final evidence item has very high confidence (near 1.0)."""
        evidence_items = load_evidence_items()
        final_item = evidence_items[-1]
        assert final_item.confidence_hint >= 0.95


class TestGetSettlementOutcome:
    """Test settlement outcome lookup."""

    def test_get_settlement_outcome_for_known_market(self):
        """Verify settlement lookup works for fixture market."""
        outcome = get_settlement_outcome("WEATHER_CHICAGO_TEMP_75_20260424")
        assert outcome is not None

    def test_settlement_outcome_structure(self):
        """Verify settlement outcome has required fields."""
        outcome = get_settlement_outcome("WEATHER_CHICAGO_TEMP_75_20260424")
        assert "actual_outcome" in outcome
        assert "settlement_price" in outcome
        assert "timestamp" in outcome

    def test_get_settlement_outcome_for_unknown_market(self):
        """Verify None is returned for unknown market."""
        outcome = get_settlement_outcome("UNKNOWN_MARKET_ID")
        assert outcome is None

    def test_settlement_outcome_values_are_consistent(self):
        """Verify outcome and price are consistent."""
        outcome = get_settlement_outcome("WEATHER_CHICAGO_TEMP_75_20260424")
        if outcome["actual_outcome"] == 1:
            assert outcome["settlement_price"] == 1.0
        elif outcome["actual_outcome"] == 0:
            assert outcome["settlement_price"] == 0.0
        else:
            pytest.fail(f"Invalid outcome: {outcome['actual_outcome']}")


class TestFixtureIntegration:
    """Integration tests between fixtures."""

    def test_snapshots_and_evidence_cover_same_time_period(self):
        """Verify snapshots and evidence span overlapping times."""
        snapshots, _ = load_market_snapshots()
        evidence_items = load_evidence_items()

        first_snapshot_time = snapshots[0].timestamp
        last_snapshot_time = snapshots[-1].timestamp

        first_evidence_time = evidence_items[0].retrieved_at
        last_evidence_time = evidence_items[-1].retrieved_at

        # Evidence should span across the snapshot period
        assert first_evidence_time <= last_snapshot_time
        assert last_evidence_time >= first_snapshot_time

    def test_snapshot_market_id_matches_settlement_key(self):
        """Verify snapshot market_id exists in settlement data."""
        snapshots, settlement_data = load_market_snapshots()

        for snapshot in snapshots:
            assert snapshot.market_id in settlement_data

    def test_all_snapshots_from_same_market(self):
        """Verify all snapshots are for the same market_id."""
        snapshots, _ = load_market_snapshots()
        market_ids = {s.market_id for s in snapshots}
        assert len(market_ids) == 1
