import type {
  AuditResponse,
  DecisionsResponse,
  HealthResponse,
  MarketsResponse,
  PaperMetricsResponse,
  ReplayMetricsResponse,
  TrialActionResult,
  TrialBookResponse,
  TrialDecisionTraceResponse,
  TrialMarketsResponse,
  TrialScenario,
  TrialScenarioRunResponse
} from "@/lib/types";

const API_BASE = process.env.API_BASE_URL ?? "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  const payload = (await response.json()) as T;
  if (!response.ok) {
    return payload;
  }
  return payload;
}

export function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/api/ui/health");
}

export function fetchMarkets(limit = 50): Promise<MarketsResponse> {
  return fetchJson<MarketsResponse>(`/api/ui/markets?limit=${limit}`);
}

export function fetchDecisions(limit = 100, marketId?: string): Promise<DecisionsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (marketId) {
    params.set("market_id", marketId);
  }
  return fetchJson<DecisionsResponse>(`/api/ui/decisions?${params.toString()}`);
}

export function fetchReplayMetrics(): Promise<ReplayMetricsResponse> {
  return fetchJson<ReplayMetricsResponse>("/api/ui/metrics/replay");
}

export function fetchPaperMetrics(): Promise<PaperMetricsResponse> {
  return fetchJson<PaperMetricsResponse>("/api/ui/metrics/paper");
}

export function fetchAudit(
  traceId?: string,
  level?: string,
  limit = 100
): Promise<AuditResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (traceId) {
    params.set("trace_id", traceId);
  }
  if (level) {
    params.set("level", level);
  }
  return fetchJson<AuditResponse>(`/api/ui/audit?${params.toString()}`);
}

export function fetchTrialMarkets(limit = 50): Promise<TrialMarketsResponse> {
  return fetchJson<TrialMarketsResponse>(`/api/trial/markets?limit=${limit}`);
}

export function fetchTrialBook(): Promise<TrialBookResponse> {
  return fetchJson<TrialBookResponse>("/api/trial/book");
}

export function fetchTrialDecisionTrace(limit = 20): Promise<TrialDecisionTraceResponse> {
  return fetchJson<TrialDecisionTraceResponse>(`/api/ui/trial-decision-trace?limit=${limit}`);
}

export function placeTrialManualBet(payload: {
  market_id: string;
  side: "YES" | "NO";
  contracts: number;
}): Promise<TrialActionResult> {
  return fetchJson<TrialActionResult>("/api/trial/bets/manual", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function placeTrialAutoBet(payload: {
  market_id: string;
  contracts: number;
}): Promise<TrialActionResult> {
  return fetchJson<TrialActionResult>("/api/trial/bets/auto", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function runTrialScenarios(payload: {
  dry_run: boolean;
  scenarios: TrialScenario[];
}): Promise<TrialScenarioRunResponse> {
  return fetchJson<TrialScenarioRunResponse>("/api/trial/scenarios/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
