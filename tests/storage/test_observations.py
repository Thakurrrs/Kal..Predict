"""Tests for durable observation storage."""

import pytest

from kal_predict.storage.paper_store import PaperStore


def make_observation(
    scan_id: str = "scan-1",
    market_id: str = "MARKET-1",
    category: str = "weather",
    parser_status: str = "supported",
    **overrides: object,
) -> dict[str, object]:
    obs = {
        "scan_id": scan_id,
        "market_id": market_id,
        "category": category,
        "subcategory": None,
        "parser_status": parser_status,
        "enabled_for_paper": True,
        "market_implied_prob": 0.41,
        "spread": 0.02,
        "volume": 1000,
        "liquidity": 5000.0,
        "close_time": "2026-06-20T00:00:00Z",
        "hours_to_close": 48.0,
        "market_status": "open",
    }
    obs.update(overrides)
    return obs


@pytest.fixture
def store(tmp_path) -> PaperStore:
    s = PaperStore(tmp_path / "obs.db")
    s.initialize()
    return s


def test_observations_table_created(store: PaperStore):
    assert "observations" in store.table_names()


def test_record_observation_inserts(store: PaperStore):
    assert store.record_observation(make_observation()) == "inserted"
    assert store.count_rows("observations") == 1


def test_same_scan_and_market_is_idempotent(store: PaperStore):
    store.record_observation(make_observation())
    assert store.record_observation(make_observation()) == "ignored"
    assert store.count_rows("observations") == 1


def test_same_market_new_scan_creates_row(store: PaperStore):
    store.record_observation(make_observation(scan_id="scan-1"))
    assert store.record_observation(make_observation(scan_id="scan-2")) == "inserted"
    assert store.count_rows("observations") == 2


def test_missing_required_field_raises(store: PaperStore):
    bad = make_observation()
    del bad["category"]
    with pytest.raises(ValueError, match="missing observation field: category"):
        store.record_observation(bad)


def test_category_summary_aggregates(store: PaperStore):
    store.record_observation(
        make_observation(market_id="W1", category="weather", parser_status="supported")
    )
    store.record_observation(
        make_observation(market_id="W2", category="weather", parser_status="supported")
    )
    store.record_observation(
        make_observation(
            market_id="S1",
            category="sports",
            subcategory="soccer",
            parser_status="supported",
            enabled_for_paper=False,
        )
    )
    summary = store.observation_category_summary()
    weather = next(r for r in summary if r["category"] == "weather")
    soccer = next(r for r in summary if r["subcategory"] == "soccer")
    assert weather["count"] == 2
    assert soccer["category"] == "sports"
    assert soccer["count"] == 1
