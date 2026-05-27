/**
 * Per-kind pictograms for graph nodes, as inline-SVG data URIs.
 *
 * Rendered by `@sigma/node-image` in `drawingMode: "background"`: the node's
 * `color` fills the disc and this white glyph is drawn on top — giving each
 * entity a recognisable "colored pin + white icon" identity (à la Neo4j Bloom
 * / Obsidian), instead of an anonymous dot.
 *
 * Glyphs are simplified lucide-style strokes on a 24×24 canvas.
 */

const STROKE =
  'fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';

// Raw inner SVG (paths) per kind — white strokes on transparent.
export const GLYPHS: Record<string, string> = {
  // skill — compact concave sparkle ("spark of ability"). Kept small + centred
  // so the area-coloured disc frames it (a big fill made nodes read as white),
  // and so it never looks like the old 8-ray loading spinner.
  skill: `<path fill="#ffffff" d="M12 6.5C12.35 10.4 13.6 11.65 17.5 12 13.6 12.35 12.35 13.6 12 17.5 11.65 13.6 10.4 12.35 6.5 12 10.4 11.65 11.65 10.4 12 6.5Z"/>`,
  // experience — briefcase
  experience: `<rect ${STROKE} x="3" y="8" width="18" height="12" rx="2"/><path ${STROKE} d="M9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>`,
  // project — layered cube
  project: `<path ${STROKE} d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M12 12v9"/>`,
  // education — graduation cap
  education: `<path ${STROKE} d="M22 10L12 5 2 10l10 5 10-5zM6 12v5c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5"/>`,
  // certification — award medal
  certification: `<circle ${STROKE} cx="12" cy="9" r="5"/><path ${STROKE} d="M9 13.5L7.5 21 12 18.5 16.5 21 15 13.5"/>`,
  // course — open book
  course: `<path ${STROKE} d="M12 6.5C10.5 5 8 4.5 4 5v13c4-.5 6.5 0 8 1.5M12 6.5C13.5 5 16 4.5 20 5v13c-4-.5-6.5 0-8 1.5M12 6.5V20"/>`,
  // language — globe
  language: `<circle ${STROKE} cx="12" cy="12" r="9"/><path ${STROKE} d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18"/>`,
  // achievement — trophy
  achievement: `<path ${STROKE} d="M7 4h10v5a5 5 0 0 1-10 0V4zM7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3M9 19h6M10 16h4v3h-4z"/>`,
  // interest — heart
  interest: `<path ${STROKE} d="M12 20s-7-4.6-7-9.3A3.7 3.7 0 0 1 12 7a3.7 3.7 0 0 1 7 3.7C19 15.4 12 20 12 20z"/>`,
  // artifact — package
  artifact: `<path ${STROKE} d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M8 5.2l8 4.6"/>`,
  // architecture_decision — git-branch / blueprint
  architecture_decision: `<circle ${STROKE} cx="7" cy="6" r="2.2"/><circle ${STROKE} cx="7" cy="18" r="2.2"/><circle ${STROKE} cx="17" cy="9" r="2.2"/><path ${STROKE} d="M7 8.2v7.6M9.2 7.4A6 6 0 0 1 15 9M14.8 9.6A6 6 0 0 1 9 16.4"/>`,
  // note — pencil/edit
  note: `<path ${STROKE} d="M5 19h14M7 15l8.5-8.5a2 2 0 0 1 3 3L10 18l-4 1 1-4z"/>`,
  // document — file with lines
  document: `<path ${STROKE} d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5zM14 3v5h5M8 13h8M8 17h6"/>`,
  // goal — target
  goal: `<circle ${STROKE} cx="12" cy="12" r="8"/><circle ${STROKE} cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1.4" fill="#ffffff"/>`,
};

const FALLBACK = `<circle ${STROKE} cx="12" cy="12" r="6"/>`;

function toDataUri(inner: string): string {
  // Explicit width/height are required so the SVG rasterizes into a WebGL
  // texture (the node-image program); a viewBox alone renders blank on canvas.
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">${inner}</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

/** kind → data-URI of a white pictogram, for the node-image program. */
export const KIND_ICONS: Record<string, string> = Object.fromEntries(
  Object.entries(GLYPHS).map(([kind, inner]) => [kind, toDataUri(inner)]),
);

const FALLBACK_ICON = toDataUri(FALLBACK);

export function iconFor(kind: string): string {
  return KIND_ICONS[kind] ?? FALLBACK_ICON;
}

/** Human-readable Spanish labels for graph edge types (shown on hover). */
export const EDGE_LABELS: Record<string, string> = {
  DEMONSTRATES: "demuestra",
  USES_TECH: "usa",
  PART_OF: "parte de",
  OCCURRED_IN: "ocurrió en",
  PRODUCED: "produjo",
  EVIDENCES_SIGNAL: "evidencia",
  LINKS_TO_ESCO: "ESCO",
  SUPERSEDES: "sustituye a",
  DERIVED_FROM: "derivado de",
  TOUCHED_IN: "tocado en",
  MEMBER_OF: "miembro de",
  RELATED_TO: "relacionado",
  generated_from: "generado de",
};

export function edgeLabel(edgeType: string | undefined): string {
  if (!edgeType) return "";
  return EDGE_LABELS[edgeType] ?? edgeType.toLowerCase().replace(/_/g, " ");
}
