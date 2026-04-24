"""Fixture loader for deterministic replay testing.

Provides access to pre-recorded market snapshots, evidence items, and settlement data
for use in replay harness and integration tests.
"""

import json
from pathlib import Path
from typing import Any, Optional

from kal_predict.models import (  # type: ignore[import-untyped]
    EvidenceItem,
    MarketSnapshot,
)


def _get_fixtures_dir() -> Path:
    """Get the path to the fixtures directory."""
    return Path(__file__).parent


def load_market_snapshots() -> tuple[list[MarketSnapshot], dict[str, Any]]:
    """Load pre-recorded market snapshots and settlement data.

    Returns:
        Tuple of (snapshots list, settlement_data dict)
        - snapshots: List of MarketSnapshot objects in chronological order
        - settlement_data: Dict mapping market_id to settlement outcome
    """
    fixtures_path = _get_fixtures_dir() / "market_data.json"

    with open(fixtures_path, "r") as f:
        data = json.load(f)

    snapshots = [MarketSnapshot(**snap) for snap in data["snapshots"]]
    settlement_data = data.get("settlement", {})

    return snapshots, settlement_data


def load_evidence_items() -> list[EvidenceItem]:
    """Load pre-recorded evidence items.

    Returns:
        List of EvidenceItem objects in chronological order
    """
    fixtures_path = _get_fixtures_dir() / "evidence_items.json"

    with open(fixtures_path, "r") as f:
        data = json.load(f)

    evidence_items = [EvidenceItem(**item) for item in data["items"]]

    return evidence_items


def get_settlement_outcome(market_id: str) -> Optional[dict[str, Any]]:
    """Get settlement data for a specific market.

    Args:
        market_id: The Kalshi market ID

    Returns:
        Settlement dict with actual_outcome, settlement_price, timestamp
        or None if market not found in fixtures
    """
    _, settlement_data = load_market_snapshots()
    return settlement_data.get(market_id)
