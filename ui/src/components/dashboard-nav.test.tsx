import React from "react";
import { render, screen } from "@testing-library/react";

import { DashboardNav } from "./dashboard-nav";

describe("DashboardNav", () => {
  it("renders all primary navigation links", () => {
    render(<DashboardNav />);
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Decision History")).toBeInTheDocument();
    expect(screen.getByText("Market Prices")).toBeInTheDocument();
    expect(screen.getByText("Practice Trading")).toBeInTheDocument();
    expect(screen.getByText("System Readiness Check")).toBeInTheDocument();
    expect(screen.getByText("Results")).toBeInTheDocument();
    expect(screen.getByText("Activity Log")).toBeInTheDocument();
  });
});
