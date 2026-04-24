"""Data contract schemas using Pydantic v2."""

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    """Current market state snapshot."""

    market_id: str = Field(..., description="Kalshi market ID")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    yes_bid: float = Field(..., ge=0, le=1, description="Best bid for YES")
    yes_ask: float = Field(..., ge=0, le=1, description="Best ask for YES")
    no_bid: float = Field(..., ge=0, le=1, description="Best bid for NO")
    no_ask: float = Field(..., ge=0, le=1, description="Best ask for NO")
    volume: int = Field(default=0, ge=0, description="Contract volume")
    schema_version: int = Field(default=1, description="Contract version")


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
    schema_version: int = Field(default=1, description="Contract version")


class TradeIntent(BaseModel):
    """Intent to execute a trade (if risk gates pass)."""

    intent_id: str = Field(..., description="Unique intent ID (UUID)")
    market_id: str = Field(..., description="Kalshi market ID")
    side: str = Field(..., description="'YES' or 'NO'")
    max_price: float = Field(..., ge=0, le=1, description="Max price to pay")
    size: int = Field(..., gt=0, description="Number of contracts")
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
