"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Home" },
  { href: "/decisions", label: "Decision History" },
  { href: "/markets", label: "Market Prices" },
  { href: "/trial", label: "Practice Trading" },
  { href: "/checklist", label: "System Readiness Check" },
  { href: "/performance", label: "Results" },
  { href: "/audit", label: "Activity Log" }
] as const;

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <ul className="nav-list">
      {items.map((item) => {
        const active = pathname === item.href;
        return (
          <li key={item.href}>
            <Link className={`nav-link${active ? " active" : ""}`} href={item.href}>
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
