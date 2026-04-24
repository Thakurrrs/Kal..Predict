import React from "react";

type KpiCardProps = {
  label: string;
  value: string;
  tone?: "ok" | "warn" | "bad" | "info";
  helperText?: string;
};

export function KpiCard({ label, value, tone = "info", helperText = "Live snapshot" }: KpiCardProps) {
  return (
    <section className="card">
      <span className={`badge ${tone}`}>{label}</span>
      <p className="kpi-value">{value}</p>
      <p className="kpi-label">{helperText}</p>
    </section>
  );
}
