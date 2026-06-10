/**
 * `present_form` (P2.D) — the agent renders an interactive multi-field form
 * card in the thread and waits for the user's values. Mirrors how
 * entityActions / genericActions use `renderAndWaitForResponse`.
 *
 * The tool result is `JSON.stringify(values)` (a `{field_id: value}` dict) or
 * the literal string 'cancelled' — matching the backend tool contract in
 * backend/src/agents/tools/ui_widgets.py.
 */
import { useCopilotAction } from "@copilotkit/react-core";
import { FormCard, type FormCardField } from "../cards/FormCard";
import type { CopilotActionParams } from "./types";

export function useFormActions() {
  useCopilotAction({
    name: "present_form",
    description:
      "Render an interactive form card in the chat (text/textarea/select/multiselect/date/number/toggle fields, pre-seeded values) and wait for the user's submission.",
    parameters: [
      { name: "form_id", type: "string", required: true },
      { name: "title", type: "string", required: true },
      { name: "fields", type: "object[]", required: true },
      { name: "submit_label", type: "string" },
      { name: "intro", type: "string" },
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
      <FormCard
        formId={(args.form_id as string) ?? "form"}
        title={(args.title as string) ?? "Completa estos datos"}
        intro={args.intro as string | undefined}
        fields={Array.isArray(args.fields) ? (args.fields as FormCardField[]) : []}
        submitLabel={(args.submit_label as string) ?? "Guardar"}
        done={status === "complete"}
        respondReady={!!respond}
        onSubmit={(values) => respond?.(JSON.stringify(values))}
        onCancel={() => respond?.("cancelled")}
      />
    ),
  });
}
