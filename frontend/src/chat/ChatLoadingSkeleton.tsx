/**
 * ChatLoadingSkeleton — the single loading placeholder for the agent chat
 * surface while CopilotKit warms up.
 *
 * Replaces three near-identical local copies (HomePage, UniversePage, and the
 * dock's DockSkeleton). Theme-aware (bg-ink/* flips with data-theme) and shaped
 * like a real conversation so the warm-up reads as "almost ready", not broken.
 */
export function ChatLoadingSkeleton() {
  return (
    <div className="flex h-full w-full max-w-[680px] mx-auto flex-col justify-end gap-4 p-4">
      <div className="flex animate-pulse gap-3">
        <div className="h-7 w-7 shrink-0 rounded-full bg-ink/10" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-3/4 rounded bg-ink/10" />
          <div className="h-3 w-1/2 rounded bg-ink/10" />
        </div>
      </div>
      <div className="flex animate-pulse justify-end gap-3">
        <div className="max-w-[70%] flex-1 space-y-2">
          <div className="h-3 w-full rounded bg-ink/10" />
          <div className="h-3 w-2/3 rounded bg-ink/10 ml-auto" />
        </div>
        <div className="h-7 w-7 shrink-0 rounded-full bg-ink/10" />
      </div>
      <div className="flex animate-pulse gap-3">
        <div className="h-7 w-7 shrink-0 rounded-full bg-ink/10" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-5/6 rounded bg-ink/10" />
          <div className="h-3 w-4/5 rounded bg-ink/10" />
          <div className="h-3 w-1/3 rounded bg-ink/10" />
        </div>
      </div>
      <div className="mt-2 h-12 rounded-card bg-ink/[0.06]" />
    </div>
  );
}
