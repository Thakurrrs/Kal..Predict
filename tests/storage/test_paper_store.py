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


def store_with_fill(tmp_path, side: str = "YES", fill_price: float = 0.40, size: int = 10):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()
    decision = make_decision()
    fill = make_fill()
    fill["side"] = side
    fill["fill_price"] = fill_price
    fill["size"] = size
    store.record_decision(decision)
    store.record_fill(fill)
    return store, fill


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


def test_record_decision_stores_created_at_timestamp(tmp_path):
    store = PaperStore(tmp_path / "paper.db")
    store.initialize()

    store.record_decision(make_decision())

    with store._connect() as connection:
        row = connection.execute("SELECT created_at FROM decisions").fetchone()

    assert row[0] != "trace-1"
    assert row[0].endswith("+00:00")


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


def test_record_yes_win_outcome_calculates_net_pnl(tmp_path):
    store, fill = store_with_fill(tmp_path, side="YES", fill_price=0.40, size=10)

    result = store.record_outcome(
        fill_id=fill["fill_id"],
        outcome_id="outcome-yes-win",
        status="won",
        resolved_at="2026-06-10T12:00:00+00:00",
    )

    assert result["write_status"] == "inserted"
    assert result["net_pnl"] == 5.8


def test_record_yes_loss_outcome_calculates_net_pnl(tmp_path):
    store, fill = store_with_fill(tmp_path, side="YES", fill_price=0.40, size=10)

    result = store.record_outcome(
        fill_id=fill["fill_id"],
        outcome_id="outcome-yes-loss",
        status="lost",
        resolved_at="2026-06-10T12:00:00+00:00",
    )

    assert result["net_pnl"] == -4.2


def test_record_no_win_and_loss_outcomes_use_side_contract_price(tmp_path):
    win_store, win_fill = store_with_fill(
        tmp_path / "win", side="NO", fill_price=0.30, size=10
    )
    loss_store, loss_fill = store_with_fill(
        tmp_path / "loss", side="NO", fill_price=0.30, size=10
    )

    win = win_store.record_outcome(
        fill_id=win_fill["fill_id"],
        outcome_id="outcome-no-win",
        status="won",
        resolved_at="2026-06-10T12:00:00+00:00",
    )
    loss = loss_store.record_outcome(
        fill_id=loss_fill["fill_id"],
        outcome_id="outcome-no-loss",
        status="lost",
        resolved_at="2026-06-10T12:00:00+00:00",
    )

    assert win["net_pnl"] == 6.8
    assert loss["net_pnl"] == -3.2


def test_record_canceled_outcome_does_not_count_as_pnl(tmp_path):
    store, fill = store_with_fill(tmp_path, side="YES", fill_price=0.40, size=10)

    result = store.record_outcome(
        fill_id=fill["fill_id"],
        outcome_id="outcome-canceled",
        status="canceled",
        resolved_at="2026-06-10T12:00:00+00:00",
    )

    assert result["net_pnl"] == 0.0
    assert result["counts_as_resolved_trade"] is False


def test_unresolved_exposure_is_reported_separately(tmp_path):
    store, _fill = store_with_fill(tmp_path, side="YES", fill_price=0.40, size=10)

    exposure = store.unresolved_exposure()

    assert exposure == 4.0


def test_duplicate_outcome_does_not_double_count_pnl(tmp_path):
    store, fill = store_with_fill(tmp_path, side="YES", fill_price=0.40, size=10)

    first = store.record_outcome(
        fill_id=fill["fill_id"],
        outcome_id="outcome-duplicate",
        status="won",
        resolved_at="2026-06-10T12:00:00+00:00",
    )
    second = store.record_outcome(
        fill_id=fill["fill_id"],
        outcome_id="outcome-duplicate-2",
        status="won",
        resolved_at="2026-06-10T12:00:00+00:00",
    )

    assert first["write_status"] == "inserted"
    assert second["write_status"] == "ignored"
    assert store.count_rows("outcomes") == 1
    assert store.realized_net_pnl() == 5.8
