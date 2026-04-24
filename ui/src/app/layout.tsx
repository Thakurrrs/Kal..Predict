import type { Metadata } from "next";
import { DashboardNav } from "@/components/dashboard-nav";
import { ThemeToggle } from "@/components/theme-toggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kal..Predict Dashboard",
  description: "Read-only operations dashboard for Kal..Predict"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="executive">
      <body>
        <main className="app-shell">
          <aside className="sidebar">
            <h1 className="brand">Kal..Predict</h1>
            <p className="brand-sub">Read-only operator console</p>
            <DashboardNav />
          </aside>

          <section className="main-area container">
            <header className="topbar">
              <div>
                <h2 className="topbar-title">Enterprise Operations Dashboard</h2>
                <p className="topbar-meta">Health, risk, performance, and audit telemetry</p>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <ThemeToggle />
                <span className="badge info">Mode: Read-only</span>
              </div>
            </header>
            {children}
          </section>
        </main>
      </body>
    </html>
  );
}
