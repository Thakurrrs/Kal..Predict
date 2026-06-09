"""Tests for durable SQLite paper trading store."""

import pytest

from kal_predict.models import Decision
from kal_predict.storage.paper_store import PaperStore


def make_decision(decision_id: str = "decision-1") -> Decision:
    return Decision(
        decision_id=decision_id,
        market_id="MARKET-1",
        mixed_probability=0.65,
        market_implied_probability=0.42,
        edge=0.23,
        expected_value=23.0,
        risk_gate_result="PASS",
        decision="BUY_YES",
        trace_id="trace-1",
        category="weather",
        gate_results={"net_edge": "PASS"},
    )


def make_fill(decision_id: str = "decision-1", fill_id: str = "fill-1") -> dict[str, object]:
    return {
        "fill_id": fill_id,
        "decision_id": decision_id,
        "market_id": "MARKET-1",
        "side": "YES",
        "fill_price": 0.42,
        "size": 10,
        "fees": 0.20,
        "timestamp": "2026-06-09T12:00:00+00:00",
        "trace_id": "trace-1",
    }


def test_paper_store_creates_required_tables(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()

    tables = store.table_names()

    assert "research_snapshots" in tables
    assert "decisions" in tables
    assert "paper_fills" in tables
    assert "outcomes" in tables
    assert "market_skips" in tables
    assert "performance_daily" in tables
    assert "source_cache" in tables


def test_record_decision_is_idempotent_by_decision_id(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()
    decision = make_decision()

    first = store.record_decision(decision)
    second = store.record_decision(decision)

    assert first == "inserted"
    assert second == "ignored"
    assert store.count_rows("decisions") == 1


def test_record_fill_prevents_duplicate_fill_for_decision(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()
    store.record_decision(make_decision())

    first = store.record_fill(make_fill())
    duplicate = store.record_fill(make_fill(fill_id="fill-2"))

    assert first == "inserted"
    assert duplicate == "ignored"
    assert store.count_rows("paper_fills") == 1


def test_record_decision_and_fill_rolls_back_on_invalid_fill(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()
    decision = make_decision()
    invalid_fill = make_fill(decision_id="")

    with pytest.raises(ValueError):
        store.record_decision_and_fill(decision, invalid_fill)

    assert store.count_rows("decisions") == 0
    assert store.count_rows("paper_fills") == 0
