import React from "react";
import { render, screen } from "@testing-library/react";

import MarketsPage from "./page";

vi.mock("@/lib/api", () => ({
  fetchMarkets: vi.fn(async () => ({
    timestamp: "2026-06-15T12:00:00Z",
    freshness_seconds: 0,
    source: "kalshi_read_only",
    provider_status: "credentialed",
    markets: [
      {
        market_id: "KXSOC-REAL-1",
        title: "Will Team A beat Team B?",
        yes_bid: 0.42,
        yes_ask: 0.45,
        no_bid: 0.55,
        no_ask: 0.58,
        volume: 1234,
        snapshot_timestamp: "2026-06-15T12:00:00Z",
        spread: 0.03,
        status: "open",
        close_time: "2026-06-16T12:00:00Z",
        category_hint: "KXSOC",
        liquidity: 2500
      }
    ]
  }))
}));

describe("MarketsPage", () => {
  it("renders market source and real read-only market fields", async () => {
    render(await MarketsPage());

    expect(screen.getByText(/Source: kalshi_read_only \(credentialed\)/)).toBeInTheDocument();
    expect(screen.getByText("KXSOC-REAL-1")).toBeInTheDocument();
    expect(screen.getByText("Will Team A beat Team B?")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
    expect(screen.getByText("2500.00")).toBeInTheDocument();
    expect(screen.getByText("2026-06-16T12:00:00Z")).toBeInTheDocument();
  });
});
