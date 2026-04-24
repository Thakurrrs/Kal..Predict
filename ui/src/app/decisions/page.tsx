import { DataState } from "@/components/data-state";
import { InfoTip } from "@/components/info-tip";
import { StatusBadge } from "@/components/status-badge";
import { fetchDecisions } from "@/lib/api";

export default async function DecisionsPage() {
  const data = await fetchDecisions(50);

  return (
    <DataState title="Decision History" subtitle={`Entries: ${data.decisions.length}`}>
      {data.decisions.length === 0 ? (
        <div className="muted">No decisions recorded yet.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th align="left">Market</th>
                <th align="left">Decision</th>
                <th align="left">Safety Check</th>
                <th align="left">
                  Edge <InfoTip text="How far our forecast is from market probability. Bigger absolute edge means stronger opportunity." />
                </th>
                <th align="left">Forecast Prob.</th>
                <th align="left">Market Prob.</th>
              </tr>
            </thead>
            <tbody>
              {data.decisions.map((item) => (
                <tr key={item.decision_id}>
                  <td>{item.market_id}</td>
                  <td>
                    <StatusBadge value={item.decision} />
                  </td>
                  <td>
                    <StatusBadge value={item.risk_gate_result} />
                  </td>
                  <td>{item.edge.toFixed(4)}</td>
                  <td>{item.mixed_probability.toFixed(4)}</td>
                  <td>{item.market_implied_probability.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DataState>
  );
}
