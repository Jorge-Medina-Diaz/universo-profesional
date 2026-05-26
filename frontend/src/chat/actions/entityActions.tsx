import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/queryKeys";
import { TimelineCard } from "../cards/TimelineCard";
import { SkillChipsCard, type SkillProposal } from "../cards/SkillChipsCard";
import { useEntityAction } from "./useEntityAction";
import { coherenceUpsert } from "./shared";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

export function useEntityActions(
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  useEntityAction(
    {
      toolName: "propose_experience",
      description: "Propose a work-experience entry. User must confirm.",
      entityKind: "experience",
      cardTitle: (a) => `${a.role ?? "?"} @ ${a.organization ?? "?"}`,
      parameters: [
        { name: "organization", type: "string", required: true },
        { name: "role", type: "string", required: true },
        { name: "start_date", type: "string" },
        { name: "end_date", type: "string" },
        { name: "is_current", type: "boolean" },
        { name: "description", type: "string" },
        { name: "highlights", type: "string[]" },
        { name: "competences", type: "string[]" },
      ] satisfies CopilotActionParams,
      renderCard: ({ args, pending, onConfirm, onReject }) => (
        <TimelineCard
          kind="experience"
          title={(args.role as string) ?? "Experiencia"}
          organization={args.organization as string | undefined}
          start_date={args.start_date as string | null}
          end_date={args.end_date as string | null}
          is_current={!!args.is_current}
          description={args.description as string | null}
          details={args as Record<string, unknown>}
          pending={pending}
          onConfirm={onConfirm}
          onReject={onReject}
          ctaLabel="Añadir experiencia"
        />
      ),
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_education",
      description: "Propose an education entry.",
      entityKind: "education",
      cardTitle: (a) => `${a.degree ?? ""} ${a.institution ?? ""}`.trim(),
      parameters: [
        { name: "institution", type: "string", required: true },
        { name: "degree", type: "string" },
        { name: "field_of_study", type: "string" },
        { name: "start_date", type: "string" },
        { name: "end_date", type: "string" },
        { name: "is_current", type: "boolean" },
        { name: "description", type: "string" },
        { name: "highlights", type: "string[]" },
      ] satisfies CopilotActionParams,
      renderCard: ({ args, pending, onConfirm, onReject }) => (
        <TimelineCard
          kind="education"
          title={
            ((args.degree as string) ||
              (args.field_of_study as string) ||
              "Educación") as string
          }
          organization={args.institution as string | undefined}
          start_date={args.start_date as string | null}
          end_date={args.end_date as string | null}
          is_current={!!args.is_current}
          description={args.description as string | null}
          details={args as Record<string, unknown>}
          pending={pending}
          onConfirm={onConfirm}
          onReject={onReject}
          ctaLabel="Añadir formación"
        />
      ),
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_project",
      description: "Propose a project entry.",
      entityKind: "project",
      cardTitle: (a) => `Proyecto: ${a.name ?? "?"}`,
      parameters: [
        { name: "name", type: "string", required: true },
        { name: "description", type: "string" },
        { name: "role", type: "string" },
        { name: "project_type", type: "string" },
        { name: "tech_stack", type: "string[]" },
        { name: "highlights", type: "string[]" },
        { name: "impact", type: "string" },
        { name: "url", type: "string" },
        { name: "is_current", type: "boolean" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_skill",
      description: "Propose a skill entry.",
      entityKind: "skill",
      cardTitle: (a) => `Skill: ${a.name ?? "?"}`,
      parameters: [
        { name: "name", type: "string", required: true },
        { name: "category", type: "string" },
        { name: "level", type: "string" },
        { name: "years", type: "number" },
        { name: "last_used_year", type: "number" },
      ] satisfies CopilotActionParams,
      buildPayload: (a) => ({ category: "hard", ...(a as Record<string, unknown>) }),
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  // Batch skills proposal — agent sends 3-6 related skills at once.
  // User toggles per-chip and tweaks level inline before committing.
  useCopilotAction({
    name: "propose_skill_batch",
    description:
      "Propose multiple related skills in a single card so the user can confirm them as a batch. Use when the user mentions a tech stack or set of competences in one breath.",
    parameters: [
      { name: "title", type: "string" },
      { name: "intro", type: "string" },
      { name: "skills", type: "object[]", required: true },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => {
      const skills = (args.skills as SkillProposal[]) ?? [];
      return (
        <SkillChipsCard
          title={(args.title as string) ?? "Skills detectadas"}
          intro={args.intro as string | undefined}
          skills={skills}
          pending={saving === "skill-batch"}
          onSubmit={async ({ accepted, rejected }) => {
            setSaving("skill-batch");
            try {
              const results: Array<{ name: string; resp: UpsertResponse | { error: string } }> = [];
              for (const s of accepted) {
                try {
                  const resp = await coherenceUpsert("skill", {
                    category: "hard",
                    ...(s as unknown as Record<string, unknown>),
                  });
                  results.push({ name: s.name, resp });
                  setLastOutcome({ kind: "skill", resp });
                } catch (e) {
                  results.push({ name: s.name, resp: { error: (e as Error).message } });
                }
              }
              qc.invalidateQueries({ queryKey: queryKeys.universe.all });
              qc.invalidateQueries({ queryKey: queryKeys.coherence.changes });
              respond?.(JSON.stringify({ accepted: results, rejected }));
            } finally {
              setSaving(null);
            }
          }}
          onCancel={() => respond?.("Rejected by user.")}
        />
      );
    },
  });

  useEntityAction(
    {
      toolName: "propose_certification",
      description: "Propose a certification entry.",
      entityKind: "certification",
      cardTitle: (a) => `Certificación: ${a.name ?? "?"}`,
      parameters: [
        { name: "name", type: "string", required: true },
        { name: "issuer", type: "string" },
        { name: "issued_on", type: "string" },
        { name: "expires_on", type: "string" },
        { name: "credential_id", type: "string" },
        { name: "verification_url", type: "string" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_course",
      description: "Propose a course entry.",
      entityKind: "course",
      cardTitle: (a) => `Curso: ${a.title ?? "?"}`,
      parameters: [
        { name: "title", type: "string", required: true },
        { name: "platform", type: "string" },
        { name: "started_on", type: "string" },
        { name: "completed_on", type: "string" },
        { name: "duration_hours", type: "number" },
        { name: "certificate_url", type: "string" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_language",
      description: "Propose a language entry (ISO-639-1 + CEFR).",
      entityKind: "language",
      cardTitle: (a) => `Idioma: ${a.name ?? ""} (${a.level ?? "?"})`,
      parameters: [
        { name: "code", type: "string", required: true },
        { name: "name", type: "string", required: true },
        { name: "level", type: "string", required: true },
        { name: "certification", type: "string" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_achievement",
      description: "Propose an achievement / award / publication / patent entry.",
      entityKind: "achievement",
      cardTitle: (a) => `Logro: ${a.title ?? "?"}`,
      parameters: [
        { name: "title", type: "string", required: true },
        { name: "achieved_on", type: "string" },
        { name: "description", type: "string" },
        { name: "context", type: "string" },
        { name: "evidence_url", type: "string" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  useEntityAction(
    {
      toolName: "propose_interest",
      description: "Propose a professional or personal interest entry.",
      entityKind: "interest",
      cardTitle: (a) => `Interés: ${a.name ?? "?"}`,
      parameters: [
        { name: "name", type: "string", required: true },
        { name: "description", type: "string" },
      ] satisfies CopilotActionParams,
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );
}
