import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CopilotProvider, useCopilotReady } from "@/app/CopilotProvider";

function TestChild() {
  const ready = useCopilotReady();
  return <div data-testid="ready">{ready ? "ready" : "not-ready"}</div>;
}

describe("CopilotProvider", () => {
  it("renders children without CopilotKit when not enabled", () => {
    render(
      <CopilotProvider>
        <TestChild />
      </CopilotProvider>
    );
    expect(screen.getByTestId("ready")).toHaveTextContent("not-ready");
  });

  it("renders children even when enabled prop is absent", () => {
    render(
      <CopilotProvider>
        <div data-testid="child">child-content</div>
      </CopilotProvider>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });
});
