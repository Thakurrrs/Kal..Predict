"""Tests for conservative paper trade sizing."""

from kal_predict.config import PaperSizingConfig
from kal_predict.core.sizing import PaperSizer


def test_sizer_returns_zero_when_net_edge_not_positive():
    result = PaperSizer(PaperSizingConfig()).size_trade(
        price=0.50,
        net_edge=0.0,
        daily_risk_used=0.0,
        category_exposure=0.0,
        series_exposure=0.0,
    )

    assert result.contracts == 0
    assert result.notional_usd == 0.0
    assert "net_edge_not_positive" in result.failed_caps


def test_sizer_returns_zero_for_invalid_prices():
    sizer = PaperSizer(PaperSizingConfig())

    zero_price = sizer.size_trade(0.0, 0.10, 0.0, 0.0, 0.0)
    one_price = sizer.size_trade(1.0, 0.10, 0.0, 0.0, 0.0)

    assert zero_price.contracts == 0
    assert one_price.contracts == 0
    assert "invalid_price" in zero_price.failed_caps
    assert "invalid_price" in one_price.failed_caps


def test_sizer_rounds_down_to_whole_contracts():
    config = PaperSizingConfig(
        bankroll_usd=1100.0,
        kelly_fraction=0.10,
        max_dollars_per_trade=11.0,
    )

    result = PaperSizer(config).size_trade(
        price=0.40,
        net_edge=0.10,
        daily_risk_used=0.0,
        category_exposure=0.0,
        series_exposure=0.0,
    )

    assert result.contracts == 27
    assert result.notional_usd == 10.8


def test_sizer_caps_max_dollars_per_trade():
    config = PaperSizingConfig(
        bankroll_usd=10000.0,
        kelly_fraction=1.0,
        max_dollars_per_trade=50.0,
    )

    result = PaperSizer(config).size_trade(
        price=0.50,
        net_edge=0.20,
        daily_risk_used=0.0,
        category_exposure=0.0,
        series_exposure=0.0,
    )

    assert result.contracts == 100
    assert result.notional_usd == 50.0
    assert "max_dollars_per_trade" in result.applied_caps


def test_sizer_respects_daily_category_and_series_caps():
    config = PaperSizingConfig(
        bankroll_usd=10000.0,
        kelly_fraction=1.0,
        max_dollars_per_trade=500.0,
        max_daily_risk_usd=100.0,
        max_category_exposure_usd=80.0,
        max_series_exposure_usd=60.0,
    )

    result = PaperSizer(config).size_trade(
        price=0.50,
        net_edge=0.20,
        daily_risk_used=50.0,
        category_exposure=30.0,
        series_exposure=20.0,
    )

    assert result.notional_usd == 40.0
    assert result.contracts == 80
    assert "max_series_exposure_usd" in result.applied_caps


def test_sizer_applies_longshot_cap():
    config = PaperSizingConfig(
        bankroll_usd=10000.0,
        kelly_fraction=1.0,
        max_dollars_per_trade=500.0,
        longshot_price_threshold=0.10,
        max_longshot_dollars=12.0,
    )

    result = PaperSizer(config).size_trade(
        price=0.05,
        net_edge=0.10,
        daily_risk_used=0.0,
        category_exposure=0.0,
        series_exposure=0.0,
    )

    assert result.notional_usd == 12.0
    assert result.contracts == 240
    assert "max_longshot_dollars" in result.applied_caps
