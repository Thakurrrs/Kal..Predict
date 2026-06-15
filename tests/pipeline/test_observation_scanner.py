"""Tests for the read-only observation scanner."""

import pytest

from kal_predict.adapters.market import MarketDataProvider
from kal_predict.models import MarketSnapshot
from kal_predict.pipeline.observation_scanner import ObservationScanner, _hours_to_close
from kal_predict.storage.paper_store import PaperStore


class FakeProvider(MarketDataProvider):
    def __init__(self, snapshots: list[MarketSnapshot]) -> None:
        self._snapshots = {s.market_id: s for s in snapshots}

    async def get_market_snapshot(self, market_id: str):
        return self._snapshots.get(market_id)

    async def list_markets(self) -> list[str]:
        return list(self._snapshots.keys())

    async def get_historical_snapshots(self, market_id, start_time, end_time):
        return []


def snap(market_id: str, title: str, close_time=None) -> MarketSnapshot:
    return MarketSnapshot(
        market_id=market_id,
        ticker=market_id,
        title=title,
        timestamp="2026-06-15T12:00:00Z",
        yes_bid=0.40,
        yes_ask=0.42,
        no_bid=0.58,
        no_ask=0.60,
        volume=1000,
        status="open",
        close_time=close_time,
    )


@pytest.fixture
def store(tmp_path) -> PaperStore:
    s = PaperStore(tmp_path / "scan.db")
    s.initialize()
    return s


@pytest.mark.asyncio
async def test_scan_records_one_observation_per_market(store: PaperStore):
    provider = FakeProvider(
        [
            snap("W1", "Will NYC get rain tomorrow?"),
            snap("E1", "Will CPI inflation exceed 3%?"),
            snap("S1", "Will Brazil win its World Cup match?"),
        ]
    )
    scanner = ObservationScanner(provider, store)
    result = await scanner.scan()

    assert result["markets_seen"] == 3
    assert result["observations_inserted"] == 3
    assert store.count_rows("observations") == 3


@pytest.mark.asyncio
async def test_scan_classifies_soccer_subcategory(store: PaperStore):
    provider = FakeProvider([snap("S1", "Will Brazil win its World Cup match?")])
    scanner = ObservationScanner(provider, store)
    await scanner.scan()

    summary = store.observation_category_summary()
    soccer = next(r for r in summary if r["subcategory"] == "soccer")
    assert soccer["category"] == "sports"


@pytest.mark.asyncio
async def test_rescan_same_markets_is_idempotent_within_scan(store: PaperStore):
    """Two distinct scans of the same market accumulate (daily volume)."""
    provider = FakeProvider([snap("W1", "Will NYC get rain tomorrow?")])
    scanner = ObservationScanner(provider, store)
    await scanner.scan()
    await scanner.scan()
    # Different scan_ids -> two rows, which is correct for volume counting.
    assert store.count_rows("observations") == 2


@pytest.mark.asyncio
async def test_scan_respects_max_markets(store: PaperStore):
    provider = FakeProvider([snap(f"M{i}", "Will NYC get rain?") for i in range(10)])
    scanner = ObservationScanner(provider, store)
    result = await scanner.scan(max_markets=3)
    assert result["markets_seen"] == 3


def test_hours_to_close_handles_missing_and_bad_values():
    from datetime import datetime, timezone

    now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert _hours_to_close(None, now) is None
    assert _hours_to_close("not-a-date", now) is None
    assert _hours_to_close("2026-06-16T12:00:00Z", now) == pytest.approx(24.0)
