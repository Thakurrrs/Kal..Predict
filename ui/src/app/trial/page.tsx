"use client";

import React from "react";
import { useEffect, useState } from "react";

import { DataState } from "@/components/data-state";
import { InfoTip } from "@/components/info-tip";
import {
  fetchTrialBook,
  fetchTrialDecisionTrace,
  fetchTrialMarkets,
  runTrialScenarios,
  placeTrialAutoBet,
  placeTrialManualBet
} from "@/lib/api";
import type {
  TrialBookResponse,
  TrialDecisionTraceItem,
  TrialMarketItem,
  TrialMarketsResponse,
  TrialScenarioRunResponse
} from "@/lib/types";

export default function TrialExchangePage() {
  const [markets, setMarkets] = useState<TrialMarketItem[]>([]);
  const [book, setBook] = useState<TrialBookResponse | null>(null);
  const [traces, setTraces] = useState<TrialDecisionTraceItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [scenarioResult, setScenarioResult] = useState<TrialScenarioRunResponse | null>(null);

  function formatDecisionMessage(
    result: { ok: boolean; error?: string; error_code?: string; details?: Record<string, unknown> },
    prefix: string
  ): string {
    if (result.ok) {
      return prefix;
    }
    const trace = result.details?.trace as
      | { trace_id?: string; edge?: number; gate_context?: { gap_threshold_pct?: number } }
      | undefined;
    if (result.error_code === "no_trade_signal") {
      const edge = typeof trace?.edge === "number" ? trace.edge : undefined;
      const threshold = trace?.gate_context?.gap_threshold_pct;
      const edgeLabel = typeof edge === "number" ? edge.toFixed(4) : "n/a";
      const thresholdLabel = typeof threshold === "number" ? threshold.toFixed(2) : "n/a";
      const traceLabel = trace?.trace_id ? ` (trace ${trace.trace_id})` : "";
      return `No auto bet placed this time: forecast and market price are too close (edge ${edgeLabel}, required ${thresholdLabel})${traceLabel}`;
    }
    const traceId =
      trace && typeof trace === "object" && "trace_id" in trace && typeof trace.trace_id === "string"
        ? trace.trace_id
        : "";
    return `Could not place the bet right now. Reason: ${result.error ?? "unknown"}${traceId ? ` (reference ${traceId})` : ""}`;
  }

  async function refresh(): Promise<void> {
    try {
      const [m, b, t]: [TrialMarketsResponse, TrialBookResponse, { traces: TrialDecisionTraceItem[] }] = await Promise.all([
        fetchTrialMarkets(25),
        fetchTrialBook(),
        fetchTrialDecisionTrace(20)
      ]);
      setMarkets(m.markets);
      setBook(b);
      setTraces(t.traces);
    } catch (_error) {
      setMessage("Unable to reach backend API. Verify backend is running and refresh.");
    }
  }

  async function placeManual(marketId: string, side: "YES" | "NO"): Promise<void> {
    setBusy(true);
    setMessage("");
    try {
      const result = await placeTrialManualBet({ market_id: marketId, side, contracts: 1 });
      setMessage(formatDecisionMessage(result, `Manual ${side} bet placed.`));
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function placeAuto(marketId: string): Promise<void> {
    setBusy(true);
    setMessage("");
    try {
      const result = await placeTrialAutoBet({ market_id: marketId, contracts: 1 });
      setMessage(formatDecisionMessage(result, "Auto bet placed from inference signal."));
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function runScenarioDryRun(): Promise<void> {
    if (markets.length === 0) {
      setMessage("Scenario dry run skipped: no markets loaded.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const target = markets[0].market_id;
      const response = await runTrialScenarios({
        dry_run: true,
        scenarios: [
          { market_id: target, mode: "auto", contracts: 1 },
          { market_id: target, mode: "manual", side: "YES", contracts: 1 }
        ]
      });
      setScenarioResult(response);
      setMessage(`Scenario dry run complete: ${response.summary.pass}/${response.summary.total} pass.`);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <DataState
      title="Practice Trading"
      subtitle="Paper-only market simulator with manual and auto decisions"
    >
      <div className="grid grid-3" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <div className="kpi-label">Trial Balance</div>
          <div className="kpi-value">${book?.balance_usd.toFixed(2) ?? "0.00"}</div>
        </div>
        <div className="card">
          <div className="kpi-label">Open Positions</div>
          <div className="kpi-value">{book ? Object.keys(book.positions).length : 0}</div>
        </div>
        <div className="card">
          <div className="kpi-label">Recent Bets</div>
          <div className="kpi-value">{book?.bets.length ?? 0}</div>
        </div>
      </div>

      {message ? <div className="muted" style={{ marginBottom: "0.75rem" }}>{message}</div> : null}

      <div className="grid grid-2" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <h3>AI Signal Details</h3>
          {markets.length === 0 ? (
            <div className="muted">No AI signal available yet.</div>
          ) : (
            <div>
              <div className="muted">Latest source: {markets[0].inference_source}</div>
              <div className="muted">Model: {markets[0].model}</div>
              <div className="muted">Latency: {markets[0].inference_latency_ms} ms</div>
              <div className="muted">Fallback reason: {markets[0].inference_fallback_reason ?? "none"}</div>
            </div>
          )}
        </div>
        <div className="card">
          <h3>Why This Decision Happened</h3>
          {traces.length === 0 ? (
            <div className="muted">No decision history yet. Place a manual or auto bet to see details.</div>
          ) : (
            <div>
              <div className="muted">Latest decision: {traces[0].decision}</div>
              <div className="muted">Safety checks: {traces[0].risk_gate_result}</div>
              <div className="muted">
                Edge <InfoTip text="Difference between our forecast probability and the market implied probability." />:{" "}
                {traces[0].edge.toFixed(4)}
              </div>
              <div className="muted">EV: {(traces[0].expected_value ?? 0).toFixed(2)}</div>
              <div className="muted">
                Requirements: confidence{" "}
                <InfoTip text="Minimum confidence needed before an action can pass safety checks." />{" "}
                {traces[0].gate_context?.min_confidence ?? "n/a"}, minimum edge {traces[0].gate_context?.gap_threshold_pct ?? "n/a"}
              </div>
              <div className="muted">Reference ID: {traces[0].trace_id}</div>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Scenario Controls (Paper Only)</h3>
        <button disabled={busy || markets.length === 0} onClick={() => void runScenarioDryRun()} style={{ marginRight: "0.4rem" }}>
          Run Dry-Run Scenario Batch
        </button>
        <div className="muted" style={{ marginTop: "0.5rem" }}>
          Runs a safe simulation batch (up to 20 scenarios). No live orders are sent.
        </div>
        {scenarioResult ? (
          <div className="muted" style={{ marginTop: "0.5rem" }}>
            Last run: pass {scenarioResult.summary.pass}, fail {scenarioResult.summary.fail}, no-trade {scenarioResult.summary.no_trade}, fallback {scenarioResult.summary.fallback_count}
          </div>
        ) : null}
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Market</th>
              <th>YES</th>
              <th>NO</th>
              <th>Implied</th>
              <th>Forecast</th>
              <th>Inference</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((item) => (
              <tr key={item.market_id}>
                <td>{item.title}</td>
                <td>{item.yes_price.toFixed(4)}</td>
                <td>{item.no_price.toFixed(4)}</td>
                <td>{item.implied_probability.toFixed(4)}</td>
                <td>{item.forecast_probability.toFixed(4)}</td>
                <td>{item.inference_source}</td>
                <td>
                  <button disabled={busy} onClick={() => void placeManual(item.market_id, "YES")} style={{ marginRight: "0.4rem" }}>
                    Buy Yes
                  </button>
                  <button disabled={busy} onClick={() => void placeManual(item.market_id, "NO")} style={{ marginRight: "0.4rem" }}>
                    Buy No
                  </button>
                  <button disabled={busy} onClick={() => void placeAuto(item.market_id)}>Auto Bet</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DataState>
  );
}
