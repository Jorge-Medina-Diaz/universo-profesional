/**
 * Graph lens + view CONTROL store — the single source of truth the AGENT and the
 * sidebar UI both write to, so the chat coordinator can pilot the /universe
 * constellation (filter, hide areas, switch lens, focus, fly the camera, pulse
 * nodes) exactly like the user can — without anyone clicking.
 *
 * The sigma renderer ([GraphView]) stays prop-driven: UniverseWorkspace reads
 * this store and feeds GraphView. The agent mutates this store via the
 * `control_graph` / `animate_graph` tools (widgetActions.tsx); the sidebar
 * toggles mutate the same setters. `present_graph_view` still drives mode/focus.
 */
import { create } from "zustand";

export type GraphLensMode =
  | "focus"
  | "cluster"
  | "timeline"
  | "outline"
  | "ontology_overlay";

export type GraphColorBy = "area" | "pillar";

/** One-shot camera/animation command consumed by GraphView's GraphEvents.
 *  `id` is monotonic so an identical command (e.g. fly to the same node twice)
 *  still fires, and a re-render never replays a stale command. */
export type GraphAnimationCmd =
  | { id: number; type: "flyTo"; entityId: string; zoom?: number; duration?: number }
  | { id: number; type: "pulse" | "highlightSet"; ids: string[]; duration?: number }
  | { id: number; type: "reset"; duration?: number };

/** Distributive omit so each union member keeps its own fields (a plain
 *  `Omit<GraphAnimationCmd,"id">` collapses the union to its common props). */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;
export type GraphAnimationInput = DistributiveOmit<GraphAnimationCmd, "id">;

/** The agent-addressable view knobs (mirror of the sidebar controls). */
export interface GraphViewPatch {
  mode: GraphLensMode;
  focusEntityId: string | null;
  depth: number;
  activeKinds: Set<string>;
  hiddenAreas: Set<string>;
  colorBy: GraphColorBy;
  search: string;
  localGraph: boolean;
  shapeByKind: boolean;
}

interface GraphLensState extends GraphViewPatch {
  /** Bumped on every set so consumers can react even to identical values. */
  revision: number;
  /** One-shot animation command (null once consumed semantics live in the UI). */
  animationCmd: GraphAnimationCmd | null;
  _animSeq: number;

  /** Legacy entry point used by `present_graph_view` — sets the lens. */
  setLens: (next: {
    mode: GraphLensMode;
    focusEntityId?: string | null;
    depth?: number;
  }) => void;
  /** Patch any subset of the view knobs (used by `control_graph` + sidebar). */
  setView: (patch: Partial<GraphViewPatch>) => void;
  toggleKind: (k: string) => void;
  clearKinds: () => void;
  toggleArea: (k: string) => void;
  clearHiddenAreas: () => void;
  /** Fire a one-shot camera/highlight animation (used by `animate_graph`). */
  animate: (cmd: GraphAnimationInput) => void;
  reset: () => void;
}

const INITIAL: GraphViewPatch & { revision: number; animationCmd: null; _animSeq: number } = {
  mode: "cluster",
  focusEntityId: null,
  depth: 2,
  activeKinds: new Set<string>(),
  hiddenAreas: new Set<string>(),
  colorBy: "area",
  search: "",
  localGraph: false,
  shapeByKind: false,
  revision: 0,
  animationCmd: null,
  _animSeq: 0,
};

export const useGraphLensState = create<GraphLensState>((set) => ({
  ...INITIAL,

  setLens: (next) =>
    set((prev) => ({
      mode: next.mode,
      focusEntityId:
        next.focusEntityId !== undefined ? next.focusEntityId : prev.focusEntityId,
      depth: next.depth ?? prev.depth,
      revision: prev.revision + 1,
    })),

  setView: (patch) =>
    set((prev) => {
      const next: Partial<GraphLensState> = { ...patch, revision: prev.revision + 1 };
      // Switching the colour lens (area↔pillar) changes the legend's group keys,
      // so a stale hidden-set would hide the wrong groups — clear it, UNLESS the
      // same patch explicitly set hiddenAreas (so the agent can do both at once).
      if (
        patch.colorBy !== undefined &&
        patch.colorBy !== prev.colorBy &&
        patch.hiddenAreas === undefined
      ) {
        next.hiddenAreas = new Set<string>();
      }
      return next;
    }),

  toggleKind: (k) =>
    set((prev) => {
      const next = new Set(prev.activeKinds);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return { activeKinds: next, revision: prev.revision + 1 };
    }),

  clearKinds: () =>
    set((prev) => ({ activeKinds: new Set<string>(), revision: prev.revision + 1 })),

  toggleArea: (k) =>
    set((prev) => {
      const next = new Set(prev.hiddenAreas);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return { hiddenAreas: next, revision: prev.revision + 1 };
    }),

  clearHiddenAreas: () =>
    set((prev) => ({ hiddenAreas: new Set<string>(), revision: prev.revision + 1 })),

  animate: (cmd) =>
    set((prev) => {
      const id = prev._animSeq + 1;
      return {
        _animSeq: id,
        animationCmd: { ...cmd, id } as GraphAnimationCmd,
        revision: prev.revision + 1,
      };
    }),

  reset: () => set({ ...INITIAL, activeKinds: new Set<string>(), hiddenAreas: new Set<string>() }),
}));
