import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { jobs, type JobStatus } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";
import { toast } from "@/ui";
import { useChatState } from "../state";
import { ConfirmCard } from "../cards/ConfirmCard";

import { JobMatchCard } from "../cards/JobMatchCard";
import { SelectFromListCard, type SelectListItem } from "../cards/SelectFromListCard";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

export function useJobActions(
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  _setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: "select_job_from_list",
    description:
      "Show the user a list of jobs and let them pick one. Returns the selected job id.",
    parameters: [
      { name: "items", type: "object[]", required: true },
      { name: "prompt", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <SelectFromListCard
        kind="jobs"
        items={((args.items as SelectListItem[]) ?? []).map((it) => ({
          ...it,
          subtitle: (it as Record<string, unknown>).company_name as string | undefined,
        }))}
        prompt={(args.prompt as string) ?? "¿Cuál?"}
        ctaLabel="Continuar"
        pending={saving === "select-job"}
        onSelect={(id) => {
          setSaving(null);
          respond?.(JSON.stringify({ selected_id: id }));
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  useCopilotAction({
    name: "propose_job_create",
    description:
      "Propose creating a new job tracker entry. The user confirms before we persist.",
    parameters: [
      { name: "title", type: "string" },
      { name: "company_name", type: "string" },
      { name: "url", type: "string" },
      { name: "description_raw", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel="Añadir oferta"
        target={(args.title as string) || (args.company_name as string) || "Nueva oferta"}
        description="Voy a añadirla a tu kanban en estado 'Interesado'."
        payload={{
          puesto: args.title,
          empresa: args.company_name,
          url: args.url,
          descripcion: args.description_raw
            ? String(args.description_raw).slice(0, 240) +
              (String(args.description_raw).length > 240 ? "…" : "")
            : undefined,
        }}
        pending={saving === "job-create"}
        confirmLabel="Añadir"
        onConfirm={async () => {
          setSaving("job-create");
          try {
            const created = await jobs.create({
              title: (args.title as string) || undefined,
              company_name: (args.company_name as string) || undefined,
              url: (args.url as string) || undefined,
              description_raw: (args.description_raw as string) || "",
              status: "interested",
            });
            qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
            toast.success("Oferta añadida");
            respond?.(JSON.stringify({ ok: true, job: created }));
          } catch (e) {
            respond?.(`error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  useCopilotAction({
    name: "propose_job_status_change",
    description:
      "Propose moving a job to a different status (kanban transition).",
    parameters: [
      { name: "job_id", type: "string", required: true },
      { name: "new_status", type: "string", required: true },
      { name: "job_title", type: "string" },
      { name: "company", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => {
      const newStatus = (args.new_status as JobStatus) ?? "applied";
      const destructive = newStatus === "archived" || newStatus === "rejected";
      return (
        <ConfirmCard
          actionLabel={`Mover a ${newStatus}`}
          target={
            (args.job_title as string) || (args.company as string) || "Oferta"
          }
          description={`Cambiar el estado en el kanban.`}
          tone={destructive ? "warn" : "default"}
          payload={{
            empresa: args.company,
            nuevo_estado: newStatus,
          }}
          pending={saving === "job-status"}
          confirmLabel="Mover"
          onConfirm={async () => {
            setSaving("job-status");
            try {
              await jobs.patch(args.job_id as string, { status: newStatus });
              qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
              toast.success("Estado actualizado");
              respond?.(JSON.stringify({ ok: true, new_status: newStatus }));
            } catch (e) {
              respond?.(`error: ${(e as Error).message}`);
            } finally {
              setSaving(null);
            }
          }}
          onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
        />
      );
    },
  });

  useCopilotAction({
    name: "propose_autopilot_run",
    description:
      "Propose running the autopilot flow (CV + cover letter + mark applied) for a specific job.",
    parameters: [
      { name: "job_id", type: "string", required: true },
      { name: "job_title", type: "string" },
      { name: "company", type: "string" },
      { name: "suggested_template", type: "string" },
      { name: "suggested_language", type: "string" },
      { name: "suggested_tone", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel="Autopilot"
        target={
          (args.job_title as string) || (args.company as string) || "Esta oferta"
        }
        description="Voy a generar CV + carta + marcar la oferta como aplicada."
        payload={{
          plantilla: args.suggested_template,
          idioma: args.suggested_language,
          tono: args.suggested_tone,
        }}
        confirmLabel="Empezar"
        onConfirm={() => {
          // Hand the launch to /jobs via the page-context channel (P2.C) —
          // JobsPage opens the AutopilotRunner for this job once loaded.
          useChatState.getState().setPendingPageContext({
            route: "/jobs",
            context: {
              job_id: args.job_id,
              template: args.suggested_template,
              language: args.suggested_language,
              tone: args.suggested_tone,
            },
          });
          window.location.hash = "#/jobs";
          respond?.(JSON.stringify({ ok: true, launched: true }));
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  useCopilotAction({
    name: "present_job_match",
    description:
      "Render a visual match scorecard after running match_job_to_profile. Pass match_score (0-100), strengths, gaps, suggested_keywords, job_title and company.",
    available: "frontend",
    parameters: [
      { name: "match_score", type: "number", required: true },
      { name: "strengths", type: "string[]" },
      { name: "gaps", type: "string[]" },
      { name: "suggested_keywords", type: "string[]" },
      { name: "job_title", type: "string" },
      { name: "company", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <JobMatchCard
        matchScore={Number(args.match_score ?? 0)}
        strengths={(args.strengths as string[]) ?? []}
        gaps={(args.gaps as string[]) ?? []}
        suggestedKeywords={(args.suggested_keywords as string[]) ?? []}
        jobTitle={args.job_title as string | undefined}
        company={args.company as string | undefined}
        onGenerate={() => (window.location.hash = "#/cv/new")}
      />
    ),
  });
}
