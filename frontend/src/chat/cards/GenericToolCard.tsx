/**
 * Generic fallback card for ANY agent tool the React layer doesn't explicitly
 * render — the wildcard (`name: "*"`) safety net so a new backend tool is never
 * dead-silent (no-silent-errors), without needing a matching component each time.
 *
 * Internal reasoning reads (get_/find_/list_/search_/match_/retrieve…) stay
 * quiet via {@link isSilentTool} so the thread isn't flooded with the agent's
 * own lookups; result-bearing / UI tools surface a subtle one-line chip.
 */

/** True for server-side reads the agent runs to think — these should NOT draw a
 *  card (they're not user-facing actions, and a card per lookup is noise). */
export function isSilentTool(name: string): boolean {
  return /^(get_|find_|list_|search_|match_|recompute_|explain_|count_|retrieve|universe_retrieve)/.test(
    name,
  );
}

export function GenericToolCard({ name, status }: { name: string; status?: string }) {
  const label = name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  const done = status === "complete";
  return (
    <div className="my-1 inline-flex items-center gap-1.5 rounded-full border border-hairline bg-canvas/60 px-2.5 py-1 text-[11px] text-stone">
      <span aria-hidden className={done ? "text-leaf" : "animate-pulse text-sunbeam-ink"}>
        {done ? "✓" : "⚙"}
      </span>
      {done ? label : `${label}…`}
    </div>
  );
}
