import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { GraphView, type GraphViewProps } from "@/graph/GraphView";
import { mockGraphSnapshot } from "../utils";

// Mock sigma ecosystem -------------------------------------------------------
const mockLoadGraph = vi.fn();
const mockRefresh = vi.fn();
const mockGetGraph = vi.fn(() => ({
  order: 0,
  size: 0,
  forEachNode: vi.fn(),
  degree: vi.fn(() => 0),
  hasNode: vi.fn(() => true),
  areNeighbors: vi.fn(() => false),
  neighbors: vi.fn(() => []),
  extremities: vi.fn(() => ["a", "b"]),
  setNodeAttribute: vi.fn(),
}));
const mockGetCamera = vi.fn(() => ({
  animatedZoom: vi.fn(),
  animatedUnzoom: vi.fn(),
  animatedReset: vi.fn(),
  ratio: 1,
  on: vi.fn(),
  off: vi.fn(),
}));
const mockGetContainer = vi.fn(() => ({ style: {} }));
const mockGetNodeDisplayData = vi.fn(() => ({ x: 0, y: 0 }));
const mockGraphToViewport = vi.fn(() => ({ x: 0, y: 0 }));
const mockViewportToGraph = vi.fn(() => ({ x: 0, y: 0 }));
const mockSetSetting = vi.fn();
const mockGetCustomBBox = vi.fn();
const mockSetCustomBBox = vi.fn();
const mockOn = vi.fn();
const mockOff = vi.fn();

vi.mock("@react-sigma/core", () => ({
  SigmaContainer: ({ children, className, settings }: {
    children: React.ReactNode;
    className?: string;
    settings?: Record<string, unknown>;
  }) => (
    <div data-testid="sigma-container" data-class={className} data-settings={JSON.stringify(settings)}>
      {children}
    </div>
  ),
  useLoadGraph: () => mockLoadGraph,
  useRegisterEvents: () => vi.fn(),
  useSigma: () => ({
    getGraph: mockGetGraph,
    getCamera: mockGetCamera,
    getContainer: mockGetContainer,
    getNodeDisplayData: mockGetNodeDisplayData,
    graphToViewport: mockGraphToViewport,
    viewportToGraph: mockViewportToGraph,
    setSetting: mockSetSetting,
    getCustomBBox: mockGetCustomBBox,
    setCustomBBox: mockSetCustomBBox,
    on: mockOn,
    off: mockOff,
    refresh: mockRefresh,
  }),
}));

vi.mock("graphology", () => ({
  default: class MockGraph {
    order = 0;
    size = 0;
    _nodes = new Map<string, Record<string, unknown>>();
    _edges = new Map<string, Record<string, unknown>>();
    constructor() {}
    addNode(key: string, attrs: Record<string, unknown>) {
      this._nodes.set(key, attrs);
      this.order++;
    }
    hasNode(key: string) {
      return this._nodes.has(key);
    }
    addEdgeWithKey(key: string, source: string, target: string, attrs: Record<string, unknown>) {
      this._edges.set(key, { source, target, ...attrs });
      this.size++;
    }
    forEachNode(cb: (node: string, attrs: Record<string, unknown>) => void) {
      for (const [k, v] of this._nodes) cb(k, v);
    }
    degree() {
      return 0;
    }
    setNodeAttribute() {}
  },
}));

vi.mock("@sigma/node-border", () => ({
  NodeBorderProgram: class {},
}));

vi.mock("@sigma/node-image", () => ({
  createNodeImageProgram: () => class {},
}));

vi.mock("sigma/rendering", () => ({
  createNodeCompoundProgram: (programs: unknown[]) => class {
    static programs = programs;
  },
}));

vi.mock("@sigma/edge-curve", () => ({
  default: class {},
  indexParallelEdgesIndex: vi.fn(),
}));

function renderGraphView(props: Partial<GraphViewProps> = {}) {
  const snapshot = mockGraphSnapshot();
  return render(
    <GraphView
      snapshot={snapshot}
      kindsFilter={undefined}
      ambient={false}
      selectedId={null}
      onSelectEntity={() => {}}
      colorBy="area"
      searchQuery={undefined}
      celebratingNodes={undefined}
      shapeByKind={false}
      showEsco={false}
      {...props}
    />,
  );
}

describe("GraphView", () => {
  it("renders with snapshot data", () => {
    renderGraphView();
    expect(screen.getByTestId("sigma-container")).toBeInTheDocument();
  });

  it("returns null when node_count is 0 and not ambient", () => {
    const { container } = renderGraphView({
      snapshot: { nodes: [], edges: [], node_count: 0, edge_count: 0 },
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders ambient mode with correct class", () => {
    renderGraphView({ ambient: true });
    const el = screen.getByTestId("sigma-container");
    expect(el).toHaveAttribute("data-class", "pointer-events-none opacity-70");
  });

  it("renders zoom control buttons with aria-labels", () => {
    renderGraphView();
    expect(screen.getByRole("button", { name: /Acercar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Alejar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Centrar/i })).toBeInTheDocument();
  });

  it("applies kindsFilter prop without error", () => {
    renderGraphView({ kindsFilter: ["skill", "experience"] });
    expect(screen.getByTestId("sigma-container")).toBeInTheDocument();
  });

  it("applies searchQuery prop without error", () => {
    renderGraphView({ searchQuery: "Python" });
    expect(screen.getByTestId("sigma-container")).toBeInTheDocument();
  });

  it("applies showEsco prop without error", () => {
    renderGraphView({ showEsco: true });
    expect(screen.getByTestId("sigma-container")).toBeInTheDocument();
  });
});
