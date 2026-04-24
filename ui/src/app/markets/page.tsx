import { DataState } from "@/components/data-state";
import { fetchMarkets } from "@/lib/api";

export default async function MarketsPage() {
  const data = await fetchMarkets(50);

  return (
    <DataState title="Market Prices" subtitle={`Markets shown: ${data.markets.length}`}>
      {data.markets.length === 0 ? (
        <div className="muted">No market price snapshots available yet.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th align="left">Market</th>
                <th align="left">YES Bid</th>
                <th align="left">YES Ask</th>
                <th align="left">NO Bid</th>
                <th align="left">NO Ask</th>
                <th align="left">Spread</th>
                <th align="left">Volume</th>
              </tr>
            </thead>
            <tbody>
              {data.markets.map((item) => (
                <tr key={`${item.market_id}-${item.snapshot_timestamp}`}>
                  <td>{item.market_id}</td>
                  <td>{item.yes_bid.toFixed(4)}</td>
                  <td>{item.yes_ask.toFixed(4)}</td>
                  <td>{item.no_bid.toFixed(4)}</td>
                  <td>{item.no_ask.toFixed(4)}</td>
                  <td>{item.spread.toFixed(4)}</td>
                  <td>{item.volume}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DataState>
  );
}
