"""Pytest configuration and fixtures."""

import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set asyncio event loop policy."""
    import asyncio

    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        # Windows
        return asyncio.WindowsSelectorEventLoopPolicy()
    return None
