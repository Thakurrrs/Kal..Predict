"""Dependency wiring for UI API services."""

from functools import lru_cache

from kal_predict.config import load_config
from kal_predict.services.ui_data import UIDataService


@lru_cache(maxsize=1)
def get_ui_service() -> UIDataService:
    """Create singleton UI data service."""
    config = load_config()
    return UIDataService(config=config)
