"""Test fixtures for market data, evidence, and replay testing.

This module provides access to pre-recorded market snapshots, evidence items,
and settlement data used in replay harness, integration tests, and mock providers.
"""

from kal_predict.fixtures.replay_sample import (
    get_settlement_outcome,
    load_evidence_items,
    load_market_snapshots,
)

__all__ = [
    "load_market_snapshots",
    "load_evidence_items",
    "get_settlement_outcome",
]
