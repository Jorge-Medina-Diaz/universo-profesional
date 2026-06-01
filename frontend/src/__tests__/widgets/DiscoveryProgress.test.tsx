import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DiscoveryProgressPill } from "@/widgets/DiscoveryProgress";
import { renderWithProviders, createTestWrapper } from "../utils";

const mockUseDiscoveryProgress = vi.fn();
vi.mock("@/shared/hooks/useDiscoveryProgress", () => ({
  useDiscoveryProgress: (...args: unknown[]) => mockUseDiscoveryProgress(...args),
}));

// The full discovery card was merged into UniverseProgress; only the compact
// header pill lives in this module now.
describe("DiscoveryProgressPill", () => {
  beforeEach(() => {
    mockUseDiscoveryProgress.mockReset();
  });

  function makeData(score: number, overrides: Record<string, unknown> = {}) {
    return {
      discovery_score: score,
      total_entities: 12,
      is_alive: true,
      ...overrides,
    };
  }

  it("renders nothing when there is no data", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: null });
    const Wrapper = createTestWrapper();
    render(<DiscoveryProgressPill />, { wrapper: Wrapper });
    expect(screen.queryByText(/\/100/)).not.toBeInTheDocument();
  });

  it("renders score and entity count", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(60) });
    renderWithProviders(<DiscoveryProgressPill />);
    expect(screen.getByText("60/100")).toBeInTheDocument();
    expect(screen.getByText("12 ent.")).toBeInTheDocument();
  });

  it("survives a discovery:celebrate event", async () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(60) });
    renderWithProviders(<DiscoveryProgressPill />);
    expect(screen.getByText("60/100")).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(
        new CustomEvent("discovery:celebrate", { detail: { score: 65, delta: 5 } }),
      );
    });
    await waitFor(() => {
      expect(screen.getByText("60/100")).toBeInTheDocument();
    });
  });
});
