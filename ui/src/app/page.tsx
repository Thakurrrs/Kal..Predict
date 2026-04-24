import { DataState } from "@/components/data-state";
import { KpiCard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { fetchHealth } from "@/lib/api";

export default async function OverviewPage() {
  const health = await fetchHealth();

  return (
    <div className="grid">
      <div className="grid grid-3">
        <KpiCard
          label="Trading Mode"
          value={health.mode.toUpperCase()}
          tone={health.mode === "paper" ? "warn" : "ok"}
          helperText="PAPER means simulation only. LIVE means real execution mode."
        />
        <KpiCard
          label="Last System Update"
          value={`${health.freshness_seconds}s`}
          tone={health.freshness_seconds > 90 ? "bad" : "ok"}
          helperText="How long since the last heartbeat. Lower is better."
        />
        <KpiCard
          label="Open Alerts"
          value={`${health.stale_data_alerts.length}`}
          tone="info"
          helperText="Count of issues that may need your attention."
        />
      </div>

      <div className="grid grid-2">
      <DataState title="System Status" subtitle={`Data source: ${health.source}`}>
        <div className="grid">
          <div>
            Trading mode: <StatusBadge value={health.mode} />
          </div>
          <div>
            System heartbeat: <StatusBadge value={health.heartbeat_status} />
          </div>
          <div>Last update time: {health.last_heartbeat_at ?? "N/A"}</div>
          <div>Seconds since update: {health.freshness_seconds}</div>
        </div>
      </DataState>

      <DataState title="Data Provider Status">
        <div className="grid">
          <div>
            Kalshi data: <StatusBadge value={health.providers.kalshi} />
          </div>
          <div>
            Weather feed (NWS): <StatusBadge value={health.providers.nws} />
          </div>
          <div>
            Search feed: <StatusBadge value={health.providers.search} />
          </div>
        </div>
      </DataState>
      </div>

      <DataState title="Alerts">
        {health.stale_data_alerts.length === 0 ? (
          <div className="muted">Everything looks good. No active alerts.</div>
        ) : (
          <ul>
            {health.stale_data_alerts.map((alert) => (
              <li key={alert}>{alert}</li>
            ))}
          </ul>
        )}
      </DataState>
    </div>
  );
}
