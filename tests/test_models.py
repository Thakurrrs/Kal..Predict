"""Tests for Pydantic data contract schemas."""

import pytest
from pydantic import ValidationError

from kal_predict.models import AuditEvent, Decision, Forecast, MarketSnapshot


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
