import React from "react";
import { render, screen } from "@testing-library/react";

import { DataState } from "./data-state";

describe("DataState", () => {
  it("renders title, subtitle, and children content", () => {
    render(
      <DataState title="Panel Title" subtitle="Panel Subtitle">
        <div>Body Content</div>
      </DataState>
    );
    expect(screen.getByText("Panel Title")).toBeInTheDocument();
    expect(screen.getByText("Panel Subtitle")).toBeInTheDocument();
    expect(screen.getByText("Body Content")).toBeInTheDocument();
  });
});
