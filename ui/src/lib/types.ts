export type ProviderStatus = "credentialed" | "configured" | "mock" | string;

export interface HealthResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  mode: string;
  heartbeat_status: string;
  last_heartbeat_at: string | null;
  providers: {
    kalshi: ProviderStatus;
    nws: ProviderStatus;
    search: ProviderStatus;
  };
  inference?: Record<string, unknown>;
  stale_data_alerts: string[];
}

export interface MarketItem {
  market_id: string;
  title: string;
  yes_bid: number;
  yes_ask: number;
  no_bid: number;
  no_ask: number;
  volume: number;
  snapshot_timestamp: string;
  spread: number;
  status: string;
  close_time: string | null;
  category_hint: string | null;
  liquidity: number | null;
}

export interface MarketsResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  provider_status: ProviderStatus;
  markets: MarketItem[];
}

export interface DecisionItem {
  decision_id: string;
  market_id: string;
  mixed_probability: number;
  market_implied_probability: number;
  edge: number;
  risk_gate_result: string;
  decision: string;
  trace_id: string;
  decision_timestamp: string;
}

export interface DecisionsResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  decisions: DecisionItem[];
}

export interface ReplayMetricsResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  brier_score: number | null;
  brier_threshold: number;
  brier_pass: boolean;
  calibration_summary: Record<string, unknown>;
  last_replay_at: string | null;
}

export interface PaperMetricsResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  paper_pnl: number;
  wins: number;
  losses: number;
  total_trades: number;
  risk_gate_failures: number;
  last_trade_at: string | null;
  unresolved_exposure: number;
}

export interface AuditEventItem {
  trace_id: string;
  event_type: string;
  actor: string;
  status: string;
  message: string;
  level: string;
  event_timestamp: string;
}

export interface AuditResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  events: AuditEventItem[];
}

export interface TrialMarketItem {
  market_id: string;
  title: string;
  yes_price: number;
  no_price: number;
  volume: number;
  implied_probability: number;
  forecast_probability: number;
  inference_source: string;
  inference_fallback_reason: string | null;
  inference_latency_ms: number;
  model: string;
  snapshot_timestamp: string;
}

export interface TrialMarketsResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  markets: TrialMarketItem[];
}

export interface TrialBet {
  bet_id: string;
  mode: string;
  market_id: string;
  side: "YES" | "NO";
  contracts: number;
  price: number;
  cost_usd: number;
  placed_at: string;
}

export interface TrialBookResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  balance_usd: number;
  positions: Record<string, number>;
  bets: TrialBet[];
}

export interface TrialDecisionTraceItem {
  trace_id: string;
  market_id: string;
  decision: string;
  risk_gate_result: string;
  edge: number;
  expected_value: number;
  inferred_probability: number;
  implied_probability: number;
  inference_source: string;
  inference_fallback_reason: string | null;
  inference_latency_ms: number;
  model: string;
  gate_context: {
    min_confidence: number;
    max_position_usd: number;
    daily_loss_limit_usd: number;
    gap_threshold_pct: number;
  };
  decision_timestamp: string;
}

export interface TrialDecisionTraceResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  traces: TrialDecisionTraceItem[];
}

export interface TrialActionResult {
  ok: boolean;
  error?: string;
  error_code?: string;
  message?: string;
  details?: Record<string, unknown>;
  bet?: TrialBet;
  balance_usd?: number;
}

export interface TrialScenario {
  market_id: string;
  mode: "manual" | "auto";
  side?: "YES" | "NO";
  contracts: number;
}

export interface TrialScenarioRunResponse {
  timestamp: string;
  freshness_seconds: number;
  source: string;
  dry_run: boolean;
  summary: {
    total: number;
    pass: number;
    fail: number;
    no_trade: number;
    fallback_count: number;
    results: TrialActionResult[];
  };
}
