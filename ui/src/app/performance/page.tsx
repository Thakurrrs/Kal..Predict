import { DataState } from "@/components/data-state";
import { InfoTip } from "@/components/info-tip";
import { KpiCard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { fetchPaperMetrics, fetchReplayMetrics } from "@/lib/api";

export default async function PerformancePage() {
  const [paper, replay] = await Promise.all([fetchPaperMetrics(), fetchReplayMetrics()]);

  return (
    <div className="grid">
      <div className="grid grid-3">
        <KpiCard
          label="Paper Profit/Loss"
          value={paper.paper_pnl.toFixed(2)}
          tone={paper.paper_pnl >= 0 ? "ok" : "bad"}
          helperText="Net result from paper bets only."
        />
        <KpiCard
          label="Total Trades"
          value={`${paper.total_trades}`}
          tone="info"
          helperText="How many paper bets were placed in this run."
        />
        <KpiCard
          label="Forecast Quality (Brier)"
          value={replay.brier_score?.toFixed(3) ?? "N/A"}
          tone={replay.brier_pass ? "ok" : "warn"}
          helperText="Lower score means better forecast accuracy."
        />
      </div>

      <div className="grid grid-2">
      <DataState title="Paper Trading Results">
        <div>Paper profit/loss: {paper.paper_pnl.toFixed(2)}</div>
        <div>Total trades: {paper.total_trades}</div>
        <div>Wins: {paper.wins}</div>
        <div>Losses: {paper.losses}</div>
        <div>Safety-check blocks: {paper.risk_gate_failures}</div>
      </DataState>

      <DataState title="Replay Quality Metrics">
        <div>
          Brier score <InfoTip text="A forecast accuracy score. Lower is better, and 0 is perfect." />:{" "}
          {replay.brier_score ?? "N/A"}
        </div>
        <div>Target Brier threshold: {replay.brier_threshold}</div>
        <div>
          Quality check: <StatusBadge value={replay.brier_pass ? "PASS" : "FAIL"} />
        </div>
        <div>Last replay run: {replay.last_replay_at ?? "N/A"}</div>
      </DataState>
      </div>
    </div>
  );
}
