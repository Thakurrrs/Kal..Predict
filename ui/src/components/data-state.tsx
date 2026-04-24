import React from "react";

type DataStateProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
};

export function DataState({ title, subtitle, children }: DataStateProps) {
  return (
    <section className="card grid">
      <h2 style={{ margin: 0 }}>{title}</h2>
      {subtitle ? <small style={{ color: "#94a3b8" }}>{subtitle}</small> : null}
      {children}
    </section>
  );
}
