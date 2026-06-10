/**
 * `present_diary_card` (Phase 3) — the agent opens the weekly career-diary
 * check-in card and waits for the user's entry. Mirrors useFormActions'
 * `renderAndWaitForResponse` shape.
 *
 * Tool result contract (backend/src/agents/tools/ui_widgets.py):
 *   - JSON string `{chips: string[], text: string}` on submit, or
 *   - the literal string 'nothing_new'.
 */
import { useCopilotAction } from "@copilotkit/react-core";
import { DiaryCard } from "../cards/DiaryCard";
import type { CopilotActionParams } from "./types";

export function useDiaryActions() {
  useCopilotAction({
    name: "present_diary_card",
    description:
      "Show the weekly career-diary check-in card (period label + optional focus-hint chips + one free-text line) and wait for the user's entry.",
    parameters: [
      { name: "period", type: "string", required: true },
      { name: "focus_hints", type: "string[]" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
      status,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
      status?: string;
    }) => (
      <DiaryCard
        period={(args.period as string) ?? ""}
        focusHints={
          Array.isArray(args.focus_hints)
            ? (args.focus_hints as unknown[]).map((h) => String(h))
            : []
        }
        done={status === "complete"}
        respondReady={!!respond}
        onSubmit={({ chips, text }) => respond?.(JSON.stringify({ chips, text }))}
        onNothingNew={() => respond?.("nothing_new")}
      />
    ),
  });
}
