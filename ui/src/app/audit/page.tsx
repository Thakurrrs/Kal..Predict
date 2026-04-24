import { DataState } from "@/components/data-state";
import { StatusBadge } from "@/components/status-badge";
import { fetchAudit } from "@/lib/api";

export default async function AuditPage() {
  const data = await fetchAudit(undefined, undefined, 100);

  return (
    <DataState title="Activity Log" subtitle={`Entries: ${data.events.length}`}>
      {data.events.length === 0 ? (
        <div className="muted">No activity events available yet.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th align="left">Time</th>
                <th align="left">Level</th>
                <th align="left">Event</th>
                <th align="left">Actor</th>
                <th align="left">Status</th>
                <th align="left">Reference</th>
                <th align="left">Message</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((event) => (
                <tr key={`${event.trace_id}-${event.event_timestamp}-${event.event_type}`}>
                  <td>{event.event_timestamp || "N/A"}</td>
                  <td>
                    <StatusBadge value={event.level} />
                  </td>
                  <td>
                    <StatusBadge value={event.event_type} />
                  </td>
                  <td>{event.actor}</td>
                  <td>
                    <StatusBadge value={event.status} />
                  </td>
                  <td>{event.trace_id}</td>
                  <td>{event.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DataState>
  );
}
