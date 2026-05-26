import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api";
import { liveProfile } from "@/shared/api-extra";
import { queryKeys } from "@/shared/queryKeys";
import { toast } from "@/ui";
import { ConfirmCard, type ConfirmTone } from "../cards/ConfirmCard";
import { EntryCard } from "../cards/EntryCard";
import {
  SelectFromListCard,
  type SelectListItem,
} from "../cards/SelectFromListCard";
import { ListPreviewCard, type PreviewItem, type PreviewKind } from "../cards/ListPreviewCard";
import { QuestionnaireCard, type QuestionnaireQuestion } from "../cards/QuestionnaireCard";
import { GoalProposalCard } from "../cards/GoalProposalCard";
import { ArtifactProposalCard, type ArtifactType } from "../cards/ArtifactProposalCard";
import { ArchitectureDecisionProposalCard } from "../cards/ArchitectureDecisionProposalCard";
import { DeepDiveCard, type DeepDiveSection } from "../cards/DeepDiveCard";
import { EscoDisambigCard, type EscoCandidate } from "../cards/EscoDisambigCard";
import { coherenceUpsert } from "./shared";
import type { SavingState, UpsertResponse, CopilotActionParams } from "./types";

export function useGenericActions(
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  _setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  // --- Batch questionnaire (A2UI) ------------------------------------------
  useCopilotAction({
    name: "present_questionnaire",
    description:
      "Show the user a batch of related questions in a single card. Each question must declare its kind (single_choice, multi_choice, scale, open).",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "questions", type: "object[]", required: true },
      { name: "submit_label", type: "string" },
      { name: "intro", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <QuestionnaireCard
        title={(args.title as string) ?? "Preguntas rápidas"}
        intro={args.intro as string | undefined}
        questions={(args.questions as QuestionnaireQuestion[]) ?? []}
        submitLabel={(args.submit_label as string) ?? "Enviar"}
        pending={saving === "questionnaire"}
        onSubmit={async (answers) => {
          setSaving("questionnaire");
          try {
            respond?.(JSON.stringify({ answers }));
          } finally {
            setSaving(null);
          }
        }}
        onCancel={() => respond?.("cancelled")}
      />
    ),
  });

  // --- Goal proposal (goals_specialist) -----------------------------------
  useCopilotAction({
    name: "propose_goal",
    description:
      "Propose creating a new professional goal. User confirms after editing fields + sub-tasks.",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "horizon", type: "string", required: true },
      { name: "description", type: "string" },
      { name: "target_date", type: "string" },
      { name: "subtasks", type: "string[]" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <GoalProposalCard
        initialTitle={(args.title as string) ?? ""}
        initialHorizon={
          ((args.horizon as string) ?? "6_months") as
            | "3_months"
            | "6_months"
            | "1_year"
            | "long_term"
        }
        initialDescription={args.description as string | undefined}
        initialTargetDate={args.target_date as string | undefined}
        initialSubtasks={(args.subtasks as string[]) ?? []}
        pending={saving === "goal-create"}
        onConfirm={async (payload) => {
          setSaving("goal-create");
          try {
            const r = await api("/api/v1/goals", {
              method: "POST",
              body: JSON.stringify(payload),
            });
            qc.invalidateQueries({ queryKey: queryKeys.goals.all });
            toast.success("Meta creada");
            respond?.(JSON.stringify({ ok: true, goal: r }));
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

  // --- Artifact proposal (portfolio first-class citizens) -----------------
  useCopilotAction({
    name: "propose_artifact",
    description:
      "Propose a portfolio artifact (github_repo|talk|blog_post|oss_contrib|paper|podcast|video|book|other). User confirms after adjusting type/title/url/year.",
    parameters: [
      { name: "type", type: "string", required: true },
      { name: "title", type: "string", required: true },
      { name: "url", type: "string", required: true },
      { name: "year", type: "number" },
      { name: "description", type: "string" },
      { name: "venue", type: "string" },
      { name: "linked_project_id", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ArtifactProposalCard
        initialType={((args.type as ArtifactType) ?? "github_repo")}
        initialTitle={(args.title as string) ?? ""}
        initialUrl={(args.url as string) ?? ""}
        initialYear={
          args.year !== undefined && args.year !== null
            ? Number(args.year)
            : undefined
        }
        initialDescription={args.description as string | undefined}
        initialVenue={args.venue as string | undefined}
        initialLinkedProjectId={args.linked_project_id as string | undefined}
        pending={saving === "artifact-create"}
        onConfirm={async (payload) => {
          setSaving("artifact-create");
          try {
            const r = await coherenceUpsert("artifact", {
              type: payload.type,
              title: payload.title,
              url: payload.url,
              year: payload.year,
              description: payload.description,
              venue: payload.venue,
              linked_project_id: payload.linked_project_id,
            });
            qc.invalidateQueries({ queryKey: queryKeys.artifacts.all });
            toast.success("Artifact guardado");
            respond?.(JSON.stringify({ ok: true, artifact: r }));
          } catch (e) {
            respond?.(`error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onCancel={() => respond?.(JSON.stringify({ approved: false, cancelled: true }))}
      />
    ),
  });

  // --- Architecture Decision Record (architecture_specialist) -------------
  useCopilotAction({
    name: "propose_architecture_decision",
    description:
      "Propose creating an Architecture Decision Record (ADR). User confirms after editing title/context/decision/consequences/status/tags.",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "context", type: "string" },
      { name: "decision", type: "string" },
      { name: "consequences", type: "string" },
      { name: "status", type: "string" },
      { name: "tags", type: "string[]" },
      { name: "related_project_id", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ArchitectureDecisionProposalCard
        initialTitle={(args.title as string) ?? ""}
        initialContext={args.context as string | undefined}
        initialDecision={args.decision as string | undefined}
        initialConsequences={args.consequences as string | undefined}
        initialStatus={
          ((args.status as string) ?? "accepted") as
            | "proposed"
            | "accepted"
            | "superseded"
            | "rejected"
        }
        initialTags={(args.tags as string[]) ?? []}
        initialRelatedProjectId={args.related_project_id as string | undefined}
        pending={saving === "adr-create"}
        onConfirm={async (payload) => {
          setSaving("adr-create");
          try {
            const r = await coherenceUpsert("architecture_decision", {
              title: payload.title,
              context: payload.context,
              decision: payload.decision,
              consequences: payload.consequences,
              status: payload.status,
              tags: payload.tags,
              related_project_id: payload.related_project_id,
            });
            qc.invalidateQueries({ queryKey: queryKeys.architectureDecisions.all });
            toast.success("ADR guardado");
            respond?.(JSON.stringify({ ok: true, adr: r }));
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

  // --- Deep dive (multi-section, curiosity_specialist) --------------------
  useCopilotAction({
    name: "present_deep_dive",
    description:
      "Multi-section deep dive for a domain the user is exploring. Sections support multi_chips, single_chips, chip_input, scale, open. Returns {topic, sections: {[id]: value}} or 'skipped'.",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "domain", type: "string", required: true },
      { name: "sections", type: "object[]", required: true },
      { name: "intro", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <DeepDiveCard
        title={(args.title as string) ?? "Cuéntame más"}
        domain={(args.domain as string) ?? "tema"}
        intro={args.intro as string | undefined}
        sections={(args.sections as DeepDiveSection[]) ?? []}
        pending={saving === "deep-dive"}
        onSubmit={async (answers) => {
          setSaving("deep-dive");
          try {
            respond?.(
              JSON.stringify({
                topic: args.domain,
                sections: answers,
              }),
            );
          } finally {
            setSaving(null);
          }
        }}
        onSkip={() => respond?.("skipped")}
      />
    ),
  });

  // --- Sprint N — ESCO disambiguation HITL --------------------------------
  useCopilotAction({
    name: "propose_esco_disambiguation",
    description:
      "Ask the user to pick the right ESCO concept for an ambiguous skill/occupation entity. Returns {chosen_uri?, dismissed: bool}.",
    parameters: [
      { name: "quarantine_id", type: "string", required: true },
      { name: "entity_kind", type: "string", required: true },
      { name: "entity_label", type: "string", required: true },
      { name: "candidates", type: "object[]", required: true },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => {
      const qid = (args.quarantine_id as string) ?? "";
      const kind = (args.entity_kind as string) ?? "skill";
      const label = (args.entity_label as string) ?? "(sin etiqueta)";
      const cands = (args.candidates as EscoCandidate[]) ?? [];
      return (
        <EscoDisambigCard
          entityKind={kind}
          entityLabel={label}
          candidates={cands}
          pending={saving === "esco-disambig"}
          onPick={async (uri) => {
            setSaving("esco-disambig");
            try {
              await api(`/api/v1/graph/quarantine/${qid}/resolve`, {
                method: "POST",
                body: JSON.stringify({
                  chosen_uri: uri,
                  resolution: "linked",
                }),
              });
              toast.success("Vinculado a la ontología");
              respond?.(JSON.stringify({ chosen_uri: uri, dismissed: false }));
            } catch (e) {
              respond?.(`error: ${(e as Error).message}`);
            } finally {
              setSaving(null);
            }
          }}
          onDismiss={async () => {
            try {
              await api(`/api/v1/graph/quarantine/${qid}/resolve`, {
                method: "POST",
                body: JSON.stringify({ resolution: "dismissed" }),
              });
            } catch {
              // best-effort — the row stays pending if the network fails
            }
            respond?.(JSON.stringify({ dismissed: true }));
          }}
        />
      );
    },
  });

  // --- Sprint N — Edge creation / deletion --------------------------------
  useCopilotAction({
    name: "propose_edge_creation",
    description:
      "Propose creating a typed graph edge between two existing entities. Returns {accepted: bool}.",
    parameters: [
      { name: "source_entity_id", type: "string", required: true },
      { name: "source_label", type: "string", required: true },
      { name: "target_entity_id", type: "string", required: true },
      { name: "target_label", type: "string", required: true },
      { name: "edge_type", type: "string", required: true },
      { name: "rationale", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel="Crear conexión"
        target={args.edge_type as string}
        description={
          <div className="space-y-1 text-sm">
            <p>
              <strong>{args.source_label as string}</strong>{" "}
              <span className="text-ink/50">
                —[{args.edge_type as string}]→
              </span>{" "}
              <strong>{args.target_label as string}</strong>
            </p>
            {args.rationale ? (
              <p className="text-ink/60 text-xs">{args.rationale as string}</p>
            ) : null}
          </div>
        }
        tone="default"
        pending={saving === "edge-create"}
        confirmLabel="Crear"
        onConfirm={async () => {
          setSaving("edge-create");
          try {
            await api("/api/v1/graph/edges", {
              method: "POST",
              body: JSON.stringify({
                source_entity_id: args.source_entity_id,
                target_entity_id: args.target_entity_id,
                edge_type: args.edge_type,
                op: "create",
              }),
            });
            toast.success("Conexión creada");
            respond?.(JSON.stringify({ accepted: true }));
          } catch (e) {
            respond?.(`error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onCancel={() => respond?.(JSON.stringify({ accepted: false }))}
      />
    ),
  });

  useCopilotAction({
    name: "propose_edge_deletion",
    description:
      "Propose expiring (soft-deleting) a typed graph edge. Returns {accepted: bool}.",
    parameters: [
      { name: "source_entity_id", type: "string", required: true },
      { name: "target_entity_id", type: "string", required: true },
      { name: "edge_type", type: "string", required: true },
      { name: "rationale", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel="Eliminar conexión"
        target={args.edge_type as string}
        description={
          <div className="space-y-1 text-sm">
            <p className="text-ink/70">
              <span className="font-mono text-xs">{args.edge_type as string}</span>
              {args.rationale ? ` · ${args.rationale as string}` : ""}
            </p>
          </div>
        }
        tone="warn"
        pending={saving === "edge-delete"}
        confirmLabel="Eliminar"
        onConfirm={async () => {
          setSaving("edge-delete");
          try {
            await api("/api/v1/graph/edges", {
              method: "POST",
              body: JSON.stringify({
                source_entity_id: args.source_entity_id,
                target_entity_id: args.target_entity_id,
                edge_type: args.edge_type,
                op: "expire",
              }),
            });
            toast.success("Conexión eliminada");
            respond?.(JSON.stringify({ accepted: true }));
          } catch (e) {
            respond?.(`error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onCancel={() => respond?.(JSON.stringify({ accepted: false }))}
      />
    ),
  });

  // --- select_document_from_list ------------------------------------------
  useCopilotAction({
    name: "select_document_from_list",
    description:
      "Show the user a list of documents and let them pick one. Returns the selected document id.",
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
        kind="documents"
        items={(args.items as SelectListItem[]) ?? []}
        prompt={(args.prompt as string) ?? "Elige un documento"}
        ctaLabel="Continuar"
        onSelect={(id) => respond?.(JSON.stringify({ selected_id: id }))}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  // --- preview_list (display-only) ----------------------------------------
  useCopilotAction({
    name: "preview_list",
    description:
      "Render a display-only list of items (jobs, documents, reminders, integrations) as cards in the chat.",
    available: "frontend",
    parameters: [
      { name: "kind", type: "string", required: true },
      { name: "items", type: "object[]", required: true },
      { name: "title", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <ListPreviewCard
        kind={(args.kind as PreviewKind) ?? "jobs"}
        items={(args.items as PreviewItem[]) ?? []}
        title={args.title as string | undefined}
      />
    ),
  });

  // --- Suggestion accept/reject -------------------------------------------
  useCopilotAction({
    name: "apply_suggestion",
    description: "Apply a stored suggestion by id. `action` must be 'accept' or 'reject'.",
    parameters: [
      { name: "suggestion_id", type: "string", required: true },
      { name: "action", type: "string", required: true },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({ args, respond }) => (
      <EntryCard
        title={`Sugerencia: ${(args.action as string) ?? "accept"}`}
        details={{ id: args.suggestion_id }}
        pending={saving === "sug"}
        ctaLabel={(args.action as string) === "reject" ? "Rechazar" : "Aceptar"}
        onConfirm={async () => {
          setSaving("sug");
          try {
            await liveProfile.suggestions.act(
              String(args.suggestion_id),
              (args.action as "accept" | "reject") ?? "accept",
            );
            qc.invalidateQueries({ queryKey: queryKeys.suggestions.all });
            respond?.("Done.");
          } catch (e) {
            respond?.(`Error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  // --- propose_preferences_update -----------------------------------------
  useCopilotAction({
    name: "propose_preferences_update",
    description:
      "Propose patching the user's career preferences. Granular patches (1-3 fields).",
    parameters: [
      { name: "patch", type: "object", required: true },
      { name: "rationale", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => {
      const patch = (args.patch as Record<string, unknown>) ?? {};
      return (
        <ConfirmCard
          actionLabel="Preferencias"
          target="Actualizar tus preferencias"
          description={(args.rationale as string) ?? undefined}
          payload={patch}
          pending={saving === "prefs"}
          confirmLabel="Guardar"
          onConfirm={async () => {
            setSaving("prefs");
            try {
              await api("/api/v1/universe/preferences", {
                method: "PUT",
                body: JSON.stringify(patch),
              });
              qc.invalidateQueries({ queryKey: queryKeys.universe.preferences });
              toast.success("Preferencias actualizadas");
              respond?.(JSON.stringify({ ok: true }));
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

  // --- confirm_destructive ------------------------------------------------
  useCopilotAction({
    name: "confirm_destructive",
    description:
      "Generic confirm gate for any action that requires explicit user approval before it runs.",
    parameters: [
      { name: "action_label", type: "string", required: true },
      { name: "target", type: "string", required: true },
      { name: "payload", type: "object" },
      { name: "tone", type: "string" },
    ] satisfies CopilotActionParams,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel={(args.action_label as string) ?? "Confirmar"}
        target={(args.target as string) ?? ""}
        payload={(args.payload as Record<string, unknown>) ?? null}
        tone={((args.tone as ConfirmTone) ?? "default") as ConfirmTone}
        onConfirm={() => respond?.(JSON.stringify({ confirmed: true }))}
        onCancel={() => respond?.(JSON.stringify({ confirmed: false }))}
      />
    ),
  });
}
