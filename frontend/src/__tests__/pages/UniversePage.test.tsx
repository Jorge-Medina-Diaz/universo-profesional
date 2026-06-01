import { screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { UniversePage } from "@/pages/UniversePage";
import { useGraphLensState } from "@/graph/lensState";
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
  // The lens store is module-global; reset it so state never leaks across tests
  // (a stale agent-set mode would otherwise change the next test's default view).
  beforeEach(() => {
    useGraphLensState.getState().reset();
  });

  it("renders the graph lens by default", async () => {
    renderWithProviders(<UniversePage />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-view")).toBeInTheDocument();
    });
  });

  it("agent switches the lens to outline (no manual switcher)", async () => {
    renderWithProviders(<UniversePage />);
    // The graph lens shows the in-graph search box; it is rendered ONLY while
    // lens === "graph" (not animated), so it's a clean signal of the active lens.
    await waitFor(
      () =>
        expect(
          screen.getByPlaceholderText(/Buscar en el grafo/i),
        ).toBeInTheDocument(),
      { timeout: 3000 },
    );

    // There is no manual lens switcher anymore — the agent drives the lens via
    // present_graph_view → useGraphLensState. Simulate that tool call.
    act(() => {
      useGraphLensState.getState().setLens({ mode: "outline" });
    });

    await waitFor(() => {
      // Leaving the graph lens removes the in-graph search box.
      expect(
        screen.queryByPlaceholderText(/Buscar en el grafo/i),
      ).not.toBeInTheDocument();
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
