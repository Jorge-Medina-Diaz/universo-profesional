import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProgressRing } from "@/ui/ProgressRing";

describe("ProgressRing", () => {
  it("renders an accessible default label from the value", () => {
    render(<ProgressRing value={42} />);
    expect(screen.getByRole("img", { name: "42% completo" })).toBeInTheDocument();
  });

  it("clamps values above 100 and below 0 in the label", () => {
    const { rerender } = render(<ProgressRing value={150} />);
    expect(screen.getByRole("img", { name: "100% completo" })).toBeInTheDocument();
    rerender(<ProgressRing value={-20} />);
    expect(screen.getByRole("img", { name: "0% completo" })).toBeInTheDocument();
  });

  it("renders center children", () => {
    render(
      <ProgressRing value={80}>
        <span>80</span>
      </ProgressRing>,
    );
    expect(screen.getByText("80")).toBeInTheDocument();
  });

  it("honours a custom aria-label", () => {
    render(<ProgressRing value={10} ariaLabel="Universo 10% completo" />);
    expect(screen.getByRole("img", { name: "Universo 10% completo" })).toBeInTheDocument();
  });
});
