"""Data contract schemas using Pydantic v2."""

from typing import Optional

from pydantic import BaseModel, Field, computed_field


class MarketSnapshot(BaseModel):
    """Current market state snapshot."""

    market_id: str = Field(..., description="Kalshi market ID")
    ticker: str = Field(default="", description="Kalshi market ticker")
    title: str = Field(default="", description="Human-readable market title")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    yes_bid: float = Field(..., ge=0, le=1, description="Best bid for YES")
    yes_ask: float = Field(..., ge=0, le=1, description="Best ask for YES")
    no_bid: float = Field(..., ge=0, le=1, description="Best bid for NO")
    no_ask: float = Field(..., ge=0, le=1, description="Best ask for NO")
    volume: int = Field(default=0, ge=0, description="Contract volume")
    status: str = Field(default="unknown", description="Market status")
    close_time: Optional[str] = Field(default=None, description="ISO8601 market close time")
    category_hint: Optional[str] = Field(default=None, description="Provider category hint")
    liquidity: Optional[float] = Field(default=None, ge=0, description="Liquidity indicator")
    schema_version: int = Field(default=1, description="Contract version")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def yes_mid(self) -> float:
        """Midpoint of executable YES bid/ask quotes."""
        return (self.yes_bid + self.yes_ask) / 2.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> float:
        """YES bid/ask spread."""
        return self.yes_ask - self.yes_bid


class EvidenceItem(BaseModel):
    """External evidence for probability updates."""

    evidence_id: str = Field(..., description="Unique evidence ID (UUID)")
    source: str = Field(..., description="Source name (e.g., 'NWS', 'news_api')")
    url: str = Field(..., description="Evidence source URL")
    retrieved_at: str = Field(..., description="ISO8601 retrieval timestamp")
    event_time: str = Field(..., description="ISO8601 time of the event")
    claim: str = Field(..., description="What the evidence claims")
    confidence_hint: float = Field(
        default=0.5, ge=0, le=1, description="How confident is this evidence"
    )
    reliability_score: float = Field(
        default=0.7, ge=0, le=1, description="Source reliability (0-1)"
    )
    schema_version: int = Field(default=1, description="Contract version")


class Signal(BaseModel):
    """Directional signal derived deterministically from research evidence."""

    source: str = Field(..., description="Signal source name")
    direction: str = Field(..., description="'YES', 'NO', or 'NEUTRAL'")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence")
    rationale: str = Field(default="", description="Human-readable signal rationale")


class SourceHealth(BaseModel):
    """Health and freshness status for a research source."""

    source: str = Field(..., description="Source name")
    status: str = Field(..., description="'ok', 'degraded', or 'failed'")
    latency_ms: int = Field(default=0, ge=0, description="Source latency in milliseconds")
    freshness_seconds: int = Field(default=0, ge=0, description="Age of source data")
    error_code: Optional[str] = Field(default=None, description="Failure code when unavailable")


class ResearchSnapshot(BaseModel):
    """Structured research output for a market."""

    research_snapshot_id: str = Field(..., description="Unique research snapshot ID")
    market_id: str = Field(..., description="Kalshi market ID")
    category: str = Field(..., description="Research category")
    usable: bool = Field(..., description="Whether downstream decisioning may use this research")
    skip_reason: Optional[str] = Field(default=None, description="Reason research is unusable")
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    source_health: list[SourceHealth] = Field(default_factory=list)
    retrieved_at: str = Field(..., description="ISO8601 retrieval timestamp")
    expires_at: str = Field(..., description="ISO8601 expiration timestamp")
    metadata: dict[str, object] = Field(default_factory=dict)
    schema_version: int = Field(default=1, description="Contract version")


class Forecast(BaseModel):
    """Probability forecast from decision engine."""

    forecast_id: str = Field(..., description="Unique forecast ID (UUID)")
    market_id: str = Field(..., description="Kalshi market ID")
    prior_probability: float = Field(..., ge=0, le=1, description="Market-implied prior")
    model_probability: float = Field(..., ge=0, le=1, description="LLM posterior estimate")
    mix_alpha: float = Field(
        default=0.7, ge=0, le=1, description="Weight for market prior (vs model)"
    )
    mixed_probability: float = Field(..., ge=0, le=1, description="Final mixed probability")
    generated_at: str = Field(..., description="ISO8601 generation timestamp")
    schema_version: int = Field(default=1, description="Contract version")


class Decision(BaseModel):
    """Risk gate evaluation and trade decision."""

    decision_id: str = Field(..., description="Unique decision ID (UUID)")
    market_id: str = Field(..., description="Kalshi market ID")
    mixed_probability: float = Field(..., ge=0, le=1, description="Our forecast")
    market_implied_probability: float = Field(..., ge=0, le=1, description="Market price")
    edge: float = Field(..., description="Divergence (our estimate - market)")
    expected_value: float = Field(..., description="Expected PnL after fees/slippage")
    risk_gate_result: str = Field(..., description="'PASS' or 'FAIL' (fail-closed)")
    decision: str = Field(..., description="'NO_TRADE', 'BUY_YES', 'BUY_NO'")
    trace_id: str = Field(..., description="Correlation ID for audit trail")
    category: str = Field(default="unknown", description="Research category")
    skip_reason: Optional[str] = Field(
        default=None, description="Primary deterministic skip reason"
    )
    gate_results: dict[str, str] = Field(
        default_factory=dict, description="Per-gate PASS/FAIL audit details"
    )
    confidence: Optional[str] = Field(default=None, description="Model confidence label")
    signals_used: list[str] = Field(
        default_factory=list, description="Signals contributing to the decision"
    )
    paper_expected_cost: Optional[float] = Field(
        default=None, ge=0, description="Expected paper cost in dollars"
    )
    schema_version: int = Field(default=1, description="Contract version")


class TradeIntent(BaseModel):
    """Intent to execute a trade (if risk gates pass)."""

    intent_id: str = Field(..., description="Unique intent ID (UUID)")
    market_id: str = Field(..., description="Kalshi market ID")
    side: str = Field(..., description="'YES' or 'NO'")
    max_price: float = Field(..., ge=0, le=1, description="Max price to pay")
    price: Optional[float] = Field(default=None, ge=0, le=1, description="Intended limit price")
    size: int = Field(..., gt=0, description="Number of contracts")
    size_dollars: Optional[float] = Field(default=None, ge=0, description="Paper order notional")
    edge: Optional[float] = Field(default=None, description="Computed edge at decision time")
    model_probability: Optional[float] = Field(
        default=None, ge=0, le=1, description="Model probability of YES"
    )
    market_price: Optional[float] = Field(
        default=None, ge=0, le=1, description="Market price used for edge"
    )
    category: str = Field(default="unknown", description="Research category")
    research_snapshot_id: Optional[str] = Field(
        default=None, description="Research snapshot that supported this intent"
    )
    mode: str = Field(
        default="paper", description="'paper' or 'live' (live blocked until Saturday)"
    )
    created_at: str = Field(..., description="ISO8601 creation timestamp")
    trace_id: str = Field(..., description="Correlation ID")
    schema_version: int = Field(default=1, description="Contract version")


class AuditEvent(BaseModel):
    """Audit trail event for compliance."""

    trace_id: str = Field(..., description="Correlation ID")
    event_type: str = Field(..., description="Type (e.g., 'FORECAST', 'RISK_GATE', 'FILL')")
    actor: str = Field(..., description="System component that created event")
    input_refs: list[str] = Field(default_factory=list, description="Input decision/evidence IDs")
    output_ref: str = Field(default="", description="Output decision/intent ID")
    status: str = Field(..., description="'SUCCESS' or 'FAIL'")
    timestamp: str = Field(..., description="ISO8601 event timestamp")
    schema_version: int = Field(default=1, description="Contract version")
