/**
 * Per-kind shape + pictogram composites for graph nodes.
 *
 * When "kind shapes" mode is active, each node renders as a distinct
 * coloured shape (square, diamond, hexagon, triangle, star, ringed-circle)
 * with its white pictogram centred on top.  This gives instant visual
 * clustering by entity type without relying on colour alone.
 *
 * The SVGs are 48×48 so they rasterise cleanly into Sigma's WebGL texture.
 */

import { KIND_COLORS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import { GLYPHS } from "./nodeIcons";

/** Shape geometry for each kind. */
const SHAPES: Record<string, (color: string) => string> = {
  experience: (c) => `<rect x="7" y="7" width="34" height="34" rx="5" fill="${c}"/>`,
  skill: (c) => `<polygon points="24,5 43,24 24,43 5,24" fill="${c}"/>`,
  project: (c) => `<polygon points="24,4 41,13 41,35 24,44 7,35 7,13" fill="${c}"/>`,
  education: (c) => `<polygon points="24,4 44,40 4,40" fill="${c}"/>`,
  certification: (c) =>
    `<circle cx="24" cy="24" r="18" fill="${c}"/><circle cx="24" cy="24" r="13" fill="none" stroke="#ffffff" stroke-width="1.5" opacity="0.45"/>`,
  goal: (c) =>
    `<polygon points="24,4 29,18 44,18 32,26 36,40 24,32 12,40 16,26 4,18 19,18" fill="${c}"/>`,
  course: (c) => `<rect x="7" y="7" width="34" height="34" rx="7" fill="${c}"/>`,
  language: (c) => `<circle cx="24" cy="24" r="18" fill="${c}"/>`,
  achievement: (c) => `<circle cx="24" cy="24" r="18" fill="${c}"/>`,
  interest: (c) => `<circle cx="24" cy="24" r="18" fill="${c}"/>`,
  artifact: (c) => `<rect x="7" y="7" width="34" height="34" rx="4" fill="${c}"/>`,
  architecture_decision: (c) => `<rect x="7" y="7" width="34" height="34" rx="3" fill="${c}"/>`,
  document: (c) => `<rect x="7" y="7" width="34" height="34" rx="2" fill="${c}"/>`,
  note: (c) => `<rect x="7" y="7" width="34" height="34" rx="3" fill="${c}"/>`,
};

const DEFAULT_SHAPE = (c: string) => `<circle cx="24" cy="24" r="18" fill="${c}"/>`;

/** White pictogram scaled + centred for the 48×48 composite canvas. */
function centeredGlyph(kind: string): string {
  const g = GLYPHS[kind];
  if (!g) return "";
  // Scale 0.7× and centre in the 48×48 canvas (centre is 24,24).
  return `<g transform="translate(24,24) scale(0.7) translate(-12,-12)">${g}</g>`;
}

function toDataUri(svg: string): string {
  const full = `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">${svg}</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(full)}`;
}

/** kind → composite shape+icon data-URI for Sigma's node-image program. */
export const KIND_SHAPES: Record<string, string> = Object.fromEntries(
  Object.keys(GLYPHS).map((kind) => {
    const color = KIND_COLORS[kind] ?? DEFAULT_KIND_COLOR;
    const shape = (SHAPES[kind] ?? DEFAULT_SHAPE)(color);
    const glyph = centeredGlyph(kind);
    return [kind, toDataUri(`${shape}${glyph}`)];
  }),
);

/** Fallback shape for unknown kinds. */
export const DEFAULT_SHAPE_ICON = toDataUri(
  DEFAULT_SHAPE(DEFAULT_KIND_COLOR) +
    `<g transform="translate(24,24) scale(0.7) translate(-12,-12)"><circle fill="none" stroke="#ffffff" stroke-width="2" cx="12" cy="12" r="6"/></g>`,
);

export function shapeFor(kind: string): string {
  return KIND_SHAPES[kind] ?? DEFAULT_SHAPE_ICON;
}
