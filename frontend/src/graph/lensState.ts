/**
 * Graph lens state — driven by the agent's `present_graph_view` tool.
 *
 * The chat coordinator can switch the /universe graph lens (and the chat
 * sidebar graph view) to a specific mode + focus node. The UniversePage
 * and GraphLens subscribe to this store so an agent turn like "let me
 * show you how your backend skills connect" pivots the visualisation
 * without the user clicking anything.
 */
import { create } from "zustand";

export type GraphLensMode =
  | "focus"
  | "cluster"
  | "timeline"
  | "outline"
  | "ontology_overlay";

interface GraphLensState {
  mode: GraphLensMode;
  focusEntityId: string | null;
  depth: number;
  /** Bumped on every set so consumers can react even to identical modes. */
  revision: number;
  setLens: (next: {
    mode: GraphLensMode;
    focusEntityId?: string | null;
    depth?: number;
  }) => void;
  reset: () => void;
}

export const useGraphLensState = create<GraphLensState>((set) => ({
  mode: "cluster",
  focusEntityId: null,
  depth: 2,
  revision: 0,
  setLens: (next) =>
    set((prev) => ({
      mode: next.mode,
      focusEntityId:
        next.focusEntityId !== undefined
          ? next.focusEntityId
          : prev.focusEntityId,
      depth: next.depth ?? prev.depth,
      revision: prev.revision + 1,
    })),
  reset: () =>
    set({ mode: "cluster", focusEntityId: null, depth: 2, revision: 0 }),
}));
