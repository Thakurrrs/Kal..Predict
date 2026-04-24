import React from "react";

type StatusBadgeProps = {
  value: string;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value.toUpperCase();
  let tone = "info";
  if (["PASS", "SUCCESS", "RUNNING", "OK"].includes(normalized)) {
    tone = "ok";
  } else if (["FAIL", "ERROR", "REJECTED"].includes(normalized)) {
    tone = "bad";
  } else if (["WARN", "WARNING", "STALE"].includes(normalized)) {
    tone = "warn";
  }
  return <span className={`badge ${tone}`}>{value}</span>;
}
