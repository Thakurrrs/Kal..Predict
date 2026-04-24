"use client";

import { useEffect, useState } from "react";

import { DataState } from "@/components/data-state";
import {
  fetchHealth,
  fetchTrialMarkets,
  placeTrialAutoBet,
  placeTrialManualBet
} from "@/lib/api";

type CheckItem = {
  name: string;
  status: "PASS" | "FAIL";
  detail: string;
};

export default function ChecklistPage() {
  const [items, setItems] = useState<CheckItem[]>([]);
  const [running, setRunning] = useState(false);

  async function runChecks(): Promise<void> {
    setRunning(true);
    const checks: CheckItem[] = [];
    try {
      const health = await fetchHealth();
      checks.push({
        name: "System status is reachable",
        status: health.timestamp ? "PASS" : "FAIL",
        detail: `mode=${health.mode}`
      });

      const markets = await fetchTrialMarkets(1);
      const first = markets.markets[0];
      checks.push({
        name: "Practice market has AI signal data",
        status: first && first.inference_source ? "PASS" : "FAIL",
        detail: first ? `source=${first.inference_source}` : "no market"
      });

      if (first) {
        const manual = await placeTrialManualBet({ market_id: first.market_id, side: "YES", contracts: 1 });
        checks.push({
          name: "Manual practice bet works",
          status: manual.ok ? "PASS" : "FAIL",
          detail: manual.ok ? "manual bet placed" : `error=${manual.error ?? "unknown"}`
        });

        const auto = await placeTrialAutoBet({ market_id: first.market_id, contracts: 1 });
        checks.push({
          name: "Auto practice bet runs",
          status: auto.ok ? "PASS" : "FAIL",
          detail: auto.ok ? "auto bet placed" : `error=${auto.error ?? "unknown"}`
        });
      }
    } catch (error) {
      checks.push({
        name: "Readiness check execution",
        status: "FAIL",
        detail: String(error)
      });
    } finally {
      setItems(checks);
      setRunning(false);
    }
  }

  useEffect(() => {
    void runChecks();
  }, []);

  return (
    <DataState
      title="System Readiness Check"
      subtitle="Quick pass/fail checks for the pre-key paper-trading setup"
    >
      <button disabled={running} onClick={() => void runChecks()} style={{ marginBottom: "0.8rem" }}>
        {running ? "Running checks..." : "Run Readiness Check"}
      </button>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.name}>
                <td>{item.name}</td>
                <td>{item.status}</td>
                <td>{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DataState>
  );
}
