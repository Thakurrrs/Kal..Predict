"""Conservative paper trade sizing."""

import math
from dataclasses import dataclass, field

from kal_predict.config import PaperSizingConfig


@dataclass(frozen=True)
class SizingResult:
    """Paper sizing decision."""

    contracts: int
    notional_usd: float
    failed_caps: list[str] = field(default_factory=list)
    applied_caps: list[str] = field(default_factory=list)


class PaperSizer:
    """Convert net edge into capped whole-contract paper size."""

    def __init__(self, config: PaperSizingConfig) -> None:
        self.config = config

    def size_trade(
        self,
        price: float,
        net_edge: float,
        daily_risk_used: float,
        category_exposure: float,
        series_exposure: float,
    ) -> SizingResult:
        """Size a paper trade using conservative fractional Kelly caps."""
        failed_caps: list[str] = []
        if net_edge <= 0:
            failed_caps.append("net_edge_not_positive")
        if price <= 0 or price >= 1:
            failed_caps.append("invalid_price")
        if failed_caps:
            return SizingResult(contracts=0, notional_usd=0.0, failed_caps=failed_caps)

        raw_dollars = self.config.bankroll_usd * net_edge * self.config.kelly_fraction
        capped_dollars, applied_caps = self._apply_caps(
            raw_dollars,
            price,
            daily_risk_used,
            category_exposure,
            series_exposure,
        )
        contracts = math.floor(capped_dollars / price)
        if contracts < self.config.min_contracts:
            return SizingResult(
                contracts=0,
                notional_usd=0.0,
                failed_caps=["below_min_contracts"],
                applied_caps=applied_caps,
            )

        notional = round(contracts * price, 10)
        return SizingResult(
            contracts=contracts,
            notional_usd=notional,
            failed_caps=[],
            applied_caps=applied_caps,
        )

    def _apply_caps(
        self,
        raw_dollars: float,
        price: float,
        daily_risk_used: float,
        category_exposure: float,
        series_exposure: float,
    ) -> tuple[float, list[str]]:
        caps = {
            "max_dollars_per_trade": self.config.max_dollars_per_trade,
            "max_daily_risk_usd": max(0.0, self.config.max_daily_risk_usd - daily_risk_used),
            "max_category_exposure_usd": max(
                0.0,
                self.config.max_category_exposure_usd - category_exposure,
            ),
            "max_series_exposure_usd": max(
                0.0,
                self.config.max_series_exposure_usd - series_exposure,
            ),
        }
        if price <= self.config.longshot_price_threshold:
            caps["max_longshot_dollars"] = self.config.max_longshot_dollars

        capped = raw_dollars
        applied: list[str] = []
        for cap_name, cap_value in caps.items():
            if cap_value < capped:
                capped = cap_value
                applied.append(cap_name)
        return max(0.0, capped), applied
