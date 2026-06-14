import React from "react";
import { render, screen, waitFor } from "@testing-library/react";

import TrialExchangePage from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchTrialMarkets: vi.fn(async () => ({
    timestamp: "2026-01-01T00:00:00Z",
    freshness_seconds: 0,
    source: "trial_exchange",
    markets: []
  })),
  fetchTrialBook: vi.fn(async () => ({
    timestamp: "2026-01-01T00:00:00Z",
    freshness_seconds: 0,
    source: "trial_exchange",
    balance_usd: 10000,
    positions: {},
    bets: []
  })),
  fetchTrialDecisionTrace: vi.fn(async () => ({
    timestamp: "2026-01-01T00:00:00Z",
    freshness_seconds: 0,
    source: "trial_exchange",
    traces: []
  })),
  placeTrialAutoBet: vi.fn(async () => ({ ok: true })),
  placeTrialManualBet: vi.fn(async () => ({ ok: true })),
  runTrialScenarios: vi.fn(async () => ({
    timestamp: "2026-01-01T00:00:00Z",
    freshness_seconds: 0,
    source: "trial_exchange",
    dry_run: true,
    summary: { total: 2, pass: 2, fail: 0, no_trade: 0, fallback_count: 0, results: [] }
  }))
}));

describe("TrialExchangePage", () => {
  it("renders loading-derived empty states", async () => {
    render(<TrialExchangePage />);
    await waitFor(() => {
      expect(screen.getByText("No AI signal available yet.")).toBeInTheDocument();
      expect(screen.getByText("No decision history yet. Place a manual or auto bet to see details.")).toBeInTheDocument();
    });
  });

  it("renders populated diagnostics and trace", async () => {
    vi.mocked(api.fetchTrialMarkets).mockResolvedValueOnce({
      timestamp: "2026-01-01T00:00:00Z",
      freshness_seconds: 0,
      source: "trial_exchange",
      markets: [
        {
          market_id: "CITY_TEMP_2026",
          title: "CITY TEMP 2026",
          yes_price: 0.61,
          no_price: 0.41,
          volume: 1000,
          implied_probability: 0.58,
          forecast_probability: 0.64,
          inference_source: "llm",
          inference_fallback_reason: null,
          inference_latency_ms: 12,
          model: "qwen",
          snapshot_timestamp: "2026-01-01T00:00:00Z"
        }
      ]
    } as never);
    vi.mocked(api.fetchTrialDecisionTrace).mockResolvedValueOnce({
      timestamp: "2026-01-01T00:00:00Z",
      freshness_seconds: 0,
      source: "trial_exchange",
      traces: [
        {
          trace_id: "trace-1",
          market_id: "CITY_TEMP_2026",
          decision: "BUY_YES",
          risk_gate_result: "PASS",
          edge: 0.06,
          expected_value: 6,
          inferred_probability: 0.64,
          implied_probability: 0.58,
          inference_source: "llm",
          inference_fallback_reason: null,
          inference_latency_ms: 12,
          model: "qwen",
          gate_context: {
            min_confidence: 0.6,
            max_position_usd: 100,
            daily_loss_limit_usd: 200,
            gap_threshold_pct: 0.05
          },
          decision_timestamp: "2026-01-01T00:00:00Z"
        }
      ]
    } as never);

    render(<TrialExchangePage />);
    await waitFor(() => {
      expect(screen.getByText("Latest decision: BUY_YES")).toBeInTheDocument();
      expect(screen.getByText("Model: qwen")).toBeInTheDocument();
      expect(screen.queryByText(/Last run:/i)).not.toBeInTheDocument();
    });
  });
});
