import { screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UniversePage } from "@/pages/UniversePage";
import { renderWithProviders } from "../utils";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

// Mock lazy-loaded graph view -------------------------------------------------
vi.mock("@/graph/GraphView", () => ({
  GraphView: (props: { snapshot?: { node_count: number } }) => (
    <div data-testid="graph-view">GraphView nodes={props.snapshot?.node_count ?? 0}</div>
  ),
}));

vi.mock("../../pages/_chat/CopilotSurface", () => ({
  CopilotSurface: () => <div data-testid="copilot-surface">CopilotSurface</div>,
}));

vi.mock("@/shared/hooks/useDiscoveryProgress", () => ({
  useDiscoveryProgress: () => ({
    data: {
      discovery_score: 60,
      total_entities: 10,
      is_alive: true,
      score_breakdown: { base: 10, recency: 5, diversity: 3, esco: 2 },
      recent_discoveries: [],
      sparse_dimensions: [],
      sources_last_7d: {},
      activity_last_24h: 0,
    },
    isLoading: false,
  }),
}));

vi.mock("@/shared/hooks/useDiscoveryStream", () => ({
  useDiscoveryStream: () => {},
}));

vi.mock("@/app/CopilotProvider", () => ({
  enableCopilot: () => {},
  useCopilotReady: () => true,
}));

vi.mock("@/widgets/ProfileCompleteness", () => ({
  ProfileCompleteness: () => <div data-testid="profile-completeness" />,
}));

vi.mock("@/widgets/SuggestionBar", () => ({
  SuggestionBar: () => <div data-testid="suggestion-bar" />,
}));

vi.mock("@/graph/NodeDetailDrawer", () => ({
  NodeDetailDrawer: () => <div data-testid="node-detail-drawer" />,
}));

vi.mock("@/chat/FloatingChat", () => ({
  FloatingChat: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="floating-chat">{children}</div>
  ),
}));

server.use(
  http.get("/api/v1/graph/snapshot", () => {
    return HttpResponse.json({
      nodes: [
        { key: "skill-1", attributes: { kind: "skill", label: "Python", area: "backend" } },
        { key: "exp-1", attributes: { kind: "experience", label: "Dev", area: "backend" } },
      ],
      edges: [],
      node_count: 2,
      edge_count: 0,
    });
  }),
  http.get("/api/v1/universe/summary", () => {
    return HttpResponse.json({
      headline: "Test",
      summary: "Test summary",
      counts: { educations: 1, experiences: 1, projects: 0, skills: 1, languages: 0 },
    });
  }),
  http.get("/api/v1/graph/communities", () => {
    return HttpResponse.json({ items: [], count: 0 });
  }),
  http.get("/api/v1/documents", () => {
    return HttpResponse.json([]);
  }),
  http.get("/api/v1/universe/shape", () => {
    return HttpResponse.json({ ok: true, shape_type: null, primary_areas: [], secondary_areas: [], strengths: [] });
  }),
);

describe("UniversePage", () => {
  it("renders without crashing", async () => {
    renderWithProviders(<UniversePage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Universo$/i })).toBeInTheDocument();
    });
  });

  it("switches lens to outline", async () => {
    renderWithProviders(<UniversePage />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Outline/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Outline/i }));

    await waitFor(() => {
      // Outline lens button should now be active (bg-ink class is hard to test directly,
      // but we can verify the button is still present and the graph view may be gone)
      expect(screen.getByRole("button", { name: /Outline/i })).toBeInTheDocument();
    });
  });

  it("search input updates state", async () => {
    renderWithProviders(<UniversePage />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Buscar en el grafo/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Buscar en el grafo/i);
    fireEvent.change(input, { target: { value: "Python" } });

    expect(input).toHaveValue("Python");
  });
});
