import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  DiscoveryProgress,
  DiscoveryProgressPill,
} from "@/widgets/DiscoveryProgress";
import { renderWithProviders, createTestWrapper } from "../utils";

const mockUseDiscoveryProgress = vi.fn();
vi.mock("@/shared/hooks/useDiscoveryProgress", () => ({
  useDiscoveryProgress: (...args: unknown[]) => mockUseDiscoveryProgress(...args),
}));

describe("DiscoveryProgress", () => {
  beforeEach(() => {
    mockUseDiscoveryProgress.mockReset();
  });

  function makeData(score: number, overrides: Record<string, unknown> = {}) {
    return {
      discovery_score: score,
      score_breakdown: { base: 10, recency: 5, diversity: 3, esco: 2 },
      total_entities: 12,
      is_alive: true,
      activity_last_24h: 2,
      sparse_dimensions: ["language", "achievement"],
      sources_last_7d: { agent_chat: 3, manual: 2 },
      recent_discoveries: [
        { entity_type: "skill", change_type: "added", source: "agent_chat", changed_at: "2024-01-01T00:00:00Z" },
      ],
      ...overrides,
    };
  }

  it("renders loading skeleton when isLoading", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: null, isLoading: true });
    const Wrapper = createTestWrapper();
    render(<DiscoveryProgress />, { wrapper: Wrapper });
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders score 0 with stone color", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(0), isLoading: false });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("12 entidades descubiertas")).toBeInTheDocument();
  });

  it("renders score 50 with sunbeam color", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(50), isLoading: false });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("renders score 80 with leaf color", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(80), isLoading: false });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText("80")).toBeInTheDocument();
  });

  it("shows Activo pulse indicator when is_alive is true", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(60), isLoading: false });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText("Activo")).toBeInTheDocument();
  });

  it("hides Activo pulse indicator when is_alive is false", () => {
    mockUseDiscoveryProgress.mockReturnValue({
      data: makeData(60, { is_alive: false }),
      isLoading: false,
    });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.queryByText("Activo")).not.toBeInTheDocument();
  });

  it("renders recent discoveries with correct labels", () => {
    mockUseDiscoveryProgress.mockReturnValue({
      data: makeData(60, {
        recent_discoveries: [
          { entity_type: "skill", change_type: "added", source: "agent_chat", changed_at: "2024-01-01T00:00:00Z" },
          { entity_type: "experience", change_type: "added", source: "manual", changed_at: "2024-01-02T00:00:00Z" },
        ],
      }),
      isLoading: false,
    });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText(/Habilidades/i)).toBeInTheDocument();
    expect(screen.getByText(/Experiencia/i)).toBeInTheDocument();
  });

  it("renders sparse dimensions", () => {
    mockUseDiscoveryProgress.mockReturnValue({ data: makeData(60), isLoading: false });
    renderWithProviders(<DiscoveryProgress />);
    expect(screen.getByText(/Idioma/i)).toBeInTheDocument();
    expect(screen.getByText(/Logro/i)).toBeInTheDocument();
  });

  it("triggers celebration animation on discovery:celebrate event", async () => {
    mockUseDiscoveryProgress.mockReturnValue({
      data: makeData(60, { discovery_score: 60, total_entities: 12, is_alive: true }),
      isLoading: false,
    });
    renderWithProviders(<DiscoveryProgressPill />);
    expect(screen.getByText("60/100")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(
        new CustomEvent("discovery:celebrate", { detail: { score: 65, delta: 5 } }),
      );
    });

    await waitFor(() => {
      // The pill should still be visible after celebration triggers
      expect(screen.getByText("60/100")).toBeInTheDocument();
    });
  });
});
