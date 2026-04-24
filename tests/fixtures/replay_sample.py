"""Fixture loader for deterministic replay testing.

Provides access to pre-recorded market snapshots, evidence items, and settlement data
for use in replay harness and integration tests.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from kal_predict.models import EvidenceItem, MarketSnapshot
from kal_predict.trace import get_trace_id
from kal_predict.utils.errors import DataValidationError

logger = logging.getLogger(__name__)


def _get_fixtures_dir() -> Path:
    """Get the path to the fixtures directory."""
    return Path(__file__).parent


def load_market_snapshots() -> tuple[list[MarketSnapshot], dict[str, Any]]:
    """Load pre-recorded market snapshots and settlement data.

    Returns:
        Tuple of (snapshots list, settlement_data dict)
        - snapshots: List of MarketSnapshot objects in chronological order
        - settlement_data: Dict mapping market_id to settlement outcome

    Raises:
        DataValidationError: If JSON is malformed or MarketSnapshot validation fails
    """
    trace_id = get_trace_id()
    fixtures_path = _get_fixtures_dir() / "market_data.json"

    try:
        with open(fixtures_path, "r") as f:
            data = json.load(f)  # Can raise json.JSONDecodeError

        snapshots = [
            MarketSnapshot(**snap) for snap in data["snapshots"]
        ]  # Can raise ValidationError
        settlement_data = data.get("settlement", {})

        return snapshots, settlement_data
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse market_data.json: {e}"
        logger.error(
            error_msg,
            extra={
                "trace_id": trace_id,
                "event_type": "data_load_error",
                "actor": "fixture_loader",
            },
        )
        raise DataValidationError(error_msg) from e
    except ValidationError as e:
        error_msg = f"Failed to validate MarketSnapshot: {e}"
        logger.error(
            error_msg,
            extra={
                "trace_id": trace_id,
                "event_type": "data_load_error",
                "actor": "fixture_loader",
            },
        )
        raise DataValidationError(error_msg) from e


def load_evidence_items() -> list[EvidenceItem]:
    """Load pre-recorded evidence items.

    Returns:
        List of EvidenceItem objects in chronological order

    Raises:
        DataValidationError: If JSON is malformed or EvidenceItem validation fails
    """
    trace_id = get_trace_id()
    fixtures_path = _get_fixtures_dir() / "evidence_items.json"

    try:
        with open(fixtures_path, "r") as f:
            data = json.load(f)  # Can raise json.JSONDecodeError

        evidence_items = [
            EvidenceItem(**item) for item in data["items"]
        ]  # Can raise ValidationError

        return evidence_items
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse evidence_items.json: {e}"
        logger.error(
            error_msg,
            extra={
                "trace_id": trace_id,
                "event_type": "data_load_error",
                "actor": "fixture_loader",
            },
        )
        raise DataValidationError(error_msg) from e
    except ValidationError as e:
        error_msg = f"Failed to validate EvidenceItem: {e}"
        logger.error(
            error_msg,
            extra={
                "trace_id": trace_id,
                "event_type": "data_load_error",
                "actor": "fixture_loader",
            },
        )
        raise DataValidationError(error_msg) from e


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
