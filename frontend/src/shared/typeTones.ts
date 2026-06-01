/**
 * Theme-aware type→tone mapping — the single source of truth for the colour of
 * every DOM chip/badge/pill that encodes a "type" (entity kind, artifact type,
 * ADR status, …).
 *
 * Why this exists: the chat HITL cards + widgets previously hardcoded raw
 * Tailwind palettes (`bg-purple-100 text-purple-800`, `text-rose-600`, …). Those
 * `*-100/*-800` pairs do NOT flip with our `data-theme="dark"` toggle (we don't
 * use Tailwind's `dark:` variant — the theme is driven by CSS custom properties),
 * so every one of them rendered as a glaring light block with vanishing text in
 * dark mode. Routing every type-tone through the cosmos palette (which already
 * has theme-aware `-soft`/`-ink` variants) fixes dark mode AND keeps the product
 * on a single, coherent 5-tone palette.
 *
 * NOTE: `shared/kindColors.ts` (raw hex) stays separate — it feeds the sigma
 * WebGL canvas, which needs literal colours, not CSS classes. Never route those
 * hex values into the DOM; never route these classes into the canvas.
 */

/** The cosmos tones that all have theme-aware `-soft` (fill) + `-ink` (text). */
export type ToneName = "leaf" | "sunbeam" | "nova" | "stone" | "danger";

/** Chip surface: soft fill + readable ink, both flip with the theme token. */
export const TONE_CLASS: Record<ToneName, string> = {
  leaf: "bg-leaf-soft text-leaf-ink",
  sunbeam: "bg-sunbeam-soft text-sunbeam-ink",
  nova: "bg-nova-soft text-nova-ink",
  stone: "bg-field text-stone",
  danger: "bg-danger-soft text-danger-ink",
};

/** Solid dot colour (for status dots / legends). */
export const TONE_DOT: Record<ToneName, string> = {
  leaf: "bg-leaf",
  sunbeam: "bg-sunbeam",
  nova: "bg-nova",
  stone: "bg-stone",
  danger: "bg-danger",
};

export const toneClass = (t: ToneName): string => TONE_CLASS[t];
export const toneDot = (t: ToneName): string => TONE_DOT[t];

/** Portfolio artifact types (ArtifactProposalCard). */
export const ARTIFACT_TONE: Record<string, ToneName> = {
  github_repo: "stone",
  talk: "nova",
  blog_post: "nova",
  oss_contrib: "leaf",
  paper: "sunbeam",
  podcast: "sunbeam",
  video: "nova",
  book: "leaf",
  other: "stone",
};

/** ADR lifecycle status (ArchitectureDecisionProposalCard). */
export const ADR_STATUS_TONE: Record<string, ToneName> = {
  proposed: "stone",
  accepted: "leaf",
  superseded: "sunbeam",
  rejected: "danger",
};

/** Universe entity kinds (ProposalCard + anywhere a kind is shown as a chip). */
export const KIND_TONE: Record<string, ToneName> = {
  skill: "leaf",
  project: "leaf",
  experience: "sunbeam",
  education: "nova",
  certification: "nova",
  course: "nova",
  language: "sunbeam",
  achievement: "sunbeam",
  interest: "leaf",
  goal: "nova",
  artifact: "stone",
  architecture_decision: "stone",
  document: "stone",
  note: "stone",
};

/** Resolve a tone from a map with a safe `stone` fallback for unknown keys. */
export function toneFor(
  map: Record<string, ToneName>,
  key: string | null | undefined,
  fallback: ToneName = "stone",
): ToneName {
  if (!key) return fallback;
  return map[key] ?? fallback;
}
