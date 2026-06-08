"""Tests for Pydantic data contract schemas."""

import pytest
from pydantic import ValidationError

from kal_predict.models import AuditEvent, Decision, Forecast, MarketSnapshot, TradeIntent


def test_market_snapshot_schema():
    """Test that MarketSnapshot validates correct data."""
    data = {
        "market_id": "WEATHER_CHICAGO_TEMP_75",
        "timestamp": "2026-04-24T12:00:00Z",
        "yes_bid": 0.65,
        "yes_ask": 0.67,
        "no_bid": 0.33,
        "no_ask": 0.35,
        "volume": 1250,
        "schema_version": 1,
    }
    snapshot = MarketSnapshot(**data)
    assert snapshot.market_id == "WEATHER_CHICAGO_TEMP_75"
    assert snapshot.yes_bid == 0.65
    assert snapshot.yes_mid == pytest.approx(0.66)
    assert snapshot.spread == pytest.approx(0.02)


def test_market_snapshot_supports_research_fields():
    """Market snapshots include fields needed for autonomous research."""
    snapshot = MarketSnapshot(
        market_id="KXCPICORE-26JUN-T3.0",
        ticker="KXCPICORE-26JUN-T3.0",
        title="Will core CPI inflation be above 3.0% in June 2026?",
        timestamp="2026-06-08T12:00:00Z",
        yes_bid=0.41,
        yes_ask=0.44,
        no_bid=0.56,
        no_ask=0.59,
        volume=4200,
        status="open",
        close_time="2026-06-10T14:00:00Z",
        category_hint="economics",
        liquidity=12000,
    )

    assert snapshot.ticker == "KXCPICORE-26JUN-T3.0"
    assert snapshot.title.startswith("Will core CPI")
    assert snapshot.status == "open"
    assert snapshot.close_time == "2026-06-10T14:00:00Z"
    assert snapshot.category_hint == "economics"
    assert snapshot.liquidity == 12000
    assert snapshot.yes_mid == pytest.approx(0.425)
    assert snapshot.spread == pytest.approx(0.03)


def test_market_snapshot_validation():
    """Test that invalid probabilities are rejected."""
    invalid_data = {
        "market_id": "TEST",
        "timestamp": "2026-04-24T00:00:00Z",
        "yes_bid": 1.5,  # Invalid: > 1.0
        "yes_ask": 0.67,
        "no_bid": 0.33,
        "no_ask": 0.35,
        "volume": 0,
    }
    with pytest.raises(ValidationError):
        MarketSnapshot(**invalid_data)


def test_forecast_schema():
    """Test Forecast schema."""
    forecast = Forecast(
        forecast_id="fc-001",
        market_id="WEATHER_CHICAGO_75",
        prior_probability=0.62,
        model_probability=0.68,
        mixed_probability=0.64,
        generated_at="2026-04-24T12:00:00Z",
    )
    assert forecast.mixed_probability == 0.64


def test_decision_schema():
    """Test Decision schema."""
    decision = Decision(
        decision_id="dec-001",
        market_id="WEATHER_CHICAGO_75",
        mixed_probability=0.64,
        market_implied_probability=0.60,
        edge=0.04,
        expected_value=12.50,
        risk_gate_result="PASS",
        decision="BUY_YES",
        trace_id="trace-abc123",
    )
    assert decision.edge == 0.04
    assert decision.risk_gate_result == "PASS"


def test_decision_supports_gate_audit_fields():
    """Decision records include category and deterministic gate audit details."""
    decision = Decision(
        decision_id="dec-002",
        market_id="KXCPICORE-26JUN-T3.0",
        mixed_probability=0.64,
        market_implied_probability=0.58,
        edge=0.06,
        expected_value=8.25,
        risk_gate_result="PASS",
        decision="BUY_YES",
        trace_id="trace-gates",
        category="economics",
        skip_reason=None,
        gate_results={"spread": "PASS", "net_edge": "PASS"},
        confidence="medium",
        signals_used=["fred_trend", "release_calendar"],
        paper_expected_cost=12.0,
    )

    assert decision.category == "economics"
    assert decision.skip_reason is None
    assert decision.gate_results["spread"] == "PASS"
    assert decision.signals_used == ["fred_trend", "release_calendar"]


def test_trade_intent_supports_profit_first_fields():
    """Trade intent keeps execution and research context for paper PnL tracking."""
    intent = TradeIntent(
        intent_id="intent-profit-001",
        market_id="KXCPICORE-26JUN-T3.0",
        side="YES",
        max_price=0.44,
        price=0.44,
        size=10,
        size_dollars=4.40,
        edge=0.06,
        model_probability=0.50,
        market_price=0.44,
        category="economics",
        research_snapshot_id="research-001",
        mode="paper",
        created_at="2026-06-08T12:00:00Z",
        trace_id="trace-profit",
    )

    assert intent.price == 0.44
    assert intent.size_dollars == 4.40
    assert intent.edge == 0.06
    assert intent.category == "economics"
    assert intent.research_snapshot_id == "research-001"


def test_audit_event_schema():
    """Test AuditEvent schema."""
    event = AuditEvent(
        trace_id="trace-abc123",
        event_type="FORECAST",
        actor="decision_engine",
        input_refs=["ev-001", "ev-002"],
        output_ref="fc-001",
        status="SUCCESS",
        timestamp="2026-04-24T12:00:00Z",
    )
    assert event.input_refs == ["ev-001", "ev-002"]
