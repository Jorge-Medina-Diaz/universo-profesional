/**
 * HITL CopilotKit actions wired to the Agno backend.
 *
 * Tool names use `snake_case` to match the Agno `@tool(external_execution=True)`
 * declarations in `backend/src/agents/tools/ui_widgets.py`. The agent emits an
 * AG-UI tool-call event; CopilotKit matches by name and `renderAndWaitForResponse`
 * shows the card. After the user confirms, the card calls the universe REST API
 * (which Agno already knows about via its own `add_*` server-side tools, but we
 * persist from the client to keep the universe REST surface as the single
 * source of truth — easier to audit and reuse from the existing pages).
 */
import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, jobs, type JobStatus } from "@/shared/api";
import { integrations, liveProfile } from "@/shared/api-extra";
import { toast } from "@/ui";
import { useChatState, type FocusEntity, type WidgetKind } from "./state";
import { useGraphLensState, type GraphLensMode } from "@/graph/lensState";
import { DiffCard } from "./cards/DiffCard";
import { EntryCard } from "./cards/EntryCard";
import { QuestionnaireCard, type QuestionnaireQuestion } from "./cards/QuestionnaireCard";
import { TimelineCard } from "./cards/TimelineCard";
import { SkillChipsCard, type SkillProposal } from "./cards/SkillChipsCard";
import { JobMatchCard } from "./cards/JobMatchCard";
// Sprint B — generic A2UI cards
import {
  SelectFromListCard,
  type SelectListItem,
} from "./cards/SelectFromListCard";
import { ListPreviewCard, type PreviewItem, type PreviewKind } from "./cards/ListPreviewCard";
import { ConfirmCard, type ConfirmTone } from "./cards/ConfirmCard";
import { DocumentPreviewCard } from "./cards/DocumentPreviewCard";
import { ProgressCard } from "./cards/ProgressCard";
import { UploadInlineCard } from "./cards/UploadInlineCard";
import { DeepDiveCard, type DeepDiveSection } from "./cards/DeepDiveCard";
import { GoalProposalCard } from "./cards/GoalProposalCard";
import {
  ArtifactProposalCard,
  type ArtifactType,
} from "./cards/ArtifactProposalCard";
import { ArchitectureDecisionProposalCard } from "./cards/ArchitectureDecisionProposalCard";
import {
  EscoDisambigCard,
  type EscoCandidate,
} from "./cards/EscoDisambigCard";

interface UpsertResponse {
  status: "created" | "merged" | "noop" | "suggested";
  entity_id: string | null;
  diffs: { field: string; old: unknown; new: unknown }[];
  suggestion_id: string | null;
  reason: string | null;
}

// Holder for the active chat thread id, updated by UniverseActions on
// every render. coherenceUpsert reads it so every entity persisted from a
// HITL card is bound to the right Episode (Sprint P) without threading the
// id through every call site.
let _activeChatSessionId: string | null = null;

async function coherenceUpsert(
  entityKind: string,
  payload: Record<string, unknown>,
): Promise<UpsertResponse> {
  return api<UpsertResponse>("/api/v1/coherence/upsert", {
    method: "POST",
    body: JSON.stringify({
      entity_type: entityKind,
      payload,
      source: "agent_chat",
      chat_session_id: _activeChatSessionId ?? undefined,
    }),
  });
}

type SavingState = string | null;

interface EntityActionConfig<TArgs> {
  toolName: string;
  description: string;
  entityKind: string;
  cardTitle: (args: TArgs) => string;
  parameters: {
    name: string;
    type: "string" | "number" | "boolean" | "string[]";
    description?: string;
    required?: boolean;
  }[];
  buildPayload?: (args: TArgs) => Record<string, unknown>;
  /** Optional card override. Falls back to EntryCard. */
  renderCard?: (ctx: {
    args: TArgs;
    pending: boolean;
    onConfirm: () => Promise<void>;
    onReject: () => void;
  }) => React.ReactElement;
}

function useEntityAction<TArgs extends Record<string, unknown>>(
  config: EntityActionConfig<TArgs>,
  saving: SavingState,
  setSaving: (s: SavingState) => void,
  setLastOutcome: (o: { kind: string; resp: UpsertResponse } | null) => void,
  qc: ReturnType<typeof useQueryClient>,
) {
  useCopilotAction({
    name: config.toolName,
    description: config.description,
    parameters: config.parameters as any,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => {
      const pending = saving === config.entityKind;
      const onConfirm = async () => {
        setSaving(config.entityKind);
        try {
          const payload = config.buildPayload
            ? config.buildPayload(args as TArgs)
            : (args as Record<string, unknown>);
          const resp = await coherenceUpsert(config.entityKind, payload);
          qc.invalidateQueries({ queryKey: ["universe"] });
          qc.invalidateQueries({ queryKey: ["coherence", "changes"] });
          setLastOutcome({ kind: config.entityKind, resp });
          respond?.(JSON.stringify(resp));
        } catch (e) {
          respond?.(`Error: ${(e as Error).message}`);
        } finally {
          setSaving(null);
        }
      };
      const onReject = () => respond?.("Rejected by user.");
      if (config.renderCard) {
        return config.renderCard({
          args: args as TArgs,
          pending,
          onConfirm,
          onReject,
        });
      }
      return (
        <EntryCard
          title={config.cardTitle(args as TArgs)}
          kind={config.entityKind}
          details={args as Record<string, unknown>}
          pending={pending}
          onConfirm={onConfirm}
          onReject={onReject}
        />
      );
    },
  });
}

export function UniverseActions() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState<SavingState>(null);
  const [lastOutcome, setLastOutcome] = useState<
    { kind: string; resp: UpsertResponse } | null
  >(null);

  // Keep the module-level chat session id in sync so coherenceUpsert can
  // bind persisted entities to the current Episode (Sprint P).
  const { threadId } = useCopilotChat();
  useEffect(() => {
    _activeChatSessionId = threadId ?? null;
  }, [threadId]);

  // --- 9 per-entity HITL cards ---------------------------------------------

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
      ],
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
      ],
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
      ],
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
      ],
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
      { name: "skills", type: "object[]", required: true } as any,
    ] as any,
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
              qc.invalidateQueries({ queryKey: ["universe"] });
              qc.invalidateQueries({ queryKey: ["coherence", "changes"] });
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
      ],
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
      ],
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
      ],
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
      ],
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
      ],
    },
    saving,
    setSaving,
    setLastOutcome,
    qc,
  );

  // --- Batch questionnaire (A2UI) ------------------------------------------

  useCopilotAction({
    name: "present_questionnaire",
    description:
      "Show the user a batch of related questions in a single card. Each question must declare its kind (single_choice, multi_choice, scale, open).",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "questions", type: "object[]", required: true } as any,
      { name: "submit_label", type: "string" },
      { name: "intro", type: "string" },
    ] as any,
    renderAndWaitForResponse: ({ args, respond }: { args: Record<string, unknown>; respond?: (s: string) => void }) => (
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
    ] as any,
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
            qc.invalidateQueries({ queryKey: ["goals"] });
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
    ] as any,
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
            // Persist immediately via the coherence engine (same as ADRs,
            // goals, and the other entity HITL paths) so the artifact lands
            // in the universe without depending on the agent making a
            // follow-up `upsert_artifact` call.
            const r = await coherenceUpsert("artifact", {
              type: payload.type,
              title: payload.title,
              url: payload.url,
              year: payload.year,
              description: payload.description,
              venue: payload.venue,
              linked_project_id: payload.linked_project_id,
            });
            qc.invalidateQueries({ queryKey: ["artifacts"] });
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
    ] as any,
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
            qc.invalidateQueries({ queryKey: ["architecture_decisions"] });
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
      { name: "sections", type: "object[]", required: true } as any,
      { name: "intro", type: "string" },
    ] as any,
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
      { name: "candidates", type: "object[]", required: true } as any,
    ] as any,
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
    ] as any,
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
    ] as any,
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

  // --- Import / sync proposals --------------------------------------------

  useCopilotAction({
    name: "propose_github_sync",
    description: "Propose pulling the user's GitHub profile. User confirms.",
    parameters: [],
    renderAndWaitForResponse: ({ respond }) => (
      <EntryCard
        title="Importar perfil de GitHub"
        details={{
          contenido: "repos · lenguajes · pinned · contributions · orgs",
          duracion: "~10-20 s",
        }}
        pending={saving === "gh-sync"}
        ctaLabel="Sincronizar ahora"
        onConfirm={async () => {
          setSaving("gh-sync");
          try {
            const r = await integrations.github.sync();
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.(`Sync ok — ${JSON.stringify(r)}`);
          } catch (e) {
            respond?.(`Sync error: ${(e as Error).message}`);
          } finally {
            setSaving(null);
          }
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  useCopilotAction({
    name: "propose_brightdata_sync",
    description: "Propose a Bright Data LinkedIn sync (PRO tier).",
    parameters: [],
    renderAndWaitForResponse: ({ respond }) => (
      <EntryCard
        title="Sincronizar LinkedIn (Bright Data, PRO)"
        details={{
          contenido: "datos públicos del perfil",
          requiere: "plan PRO + URL pública",
        }}
        pending={saving === "brightdata"}
        ctaLabel="Ir a Conexiones"
        onConfirm={async () => {
          setSaving("brightdata");
          window.location.assign("/connections");
          respond?.("Redirected to /connections.");
          setSaving(null);
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  useCopilotAction({
    name: "propose_pdf_import",
    description: "Propose uploading a CV PDF for import.",
    parameters: [],
    renderAndWaitForResponse: ({ respond }) => (
      <EntryCard
        title="Subir un CV en PDF"
        details={{ formato: "PDF", maximo: "10 MB" }}
        pending={false}
        ctaLabel="Ir a Conexiones"
        onConfirm={() => {
          window.location.assign("/connections");
          respond?.("Redirected to /connections.");
        }}
        onReject={() => respond?.("Cancelled.")}
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
    ],
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
            qc.invalidateQueries({ queryKey: ["suggestions"] });
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

  // --- Cover letter proposal ---------------------------------------------
  // Agent uses this after detecting the user wants a cover letter for a JD.
  // We render an EntryCard that, on confirm, drops the user into the CV
  // generator with the JD prefilled and kind=cover_letter pre-selected.
  useCopilotAction({
    name: "propose_cover_letter",
    description:
      "Offer to generate a cover letter for a job description. Pass job_description and optional job_url + company + title.",
    parameters: [
      { name: "job_description", type: "string", required: true },
      { name: "job_url", type: "string" },
      { name: "company", type: "string" },
      { name: "title", type: "string" },
    ] as any,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <EntryCard
        title="Generar carta de presentación"
        kind="cover_letter"
        details={{
          puesto: args.title as string | undefined,
          empresa: args.company as string | undefined,
          fuente: args.job_url as string | undefined,
        }}
        pending={false}
        ctaLabel="Abrir generador"
        ctaDescription="Te llevamos al generador con la oferta y el modo carta pre-seleccionados."
        onConfirm={() => {
          try {
            sessionStorage.setItem(
              "cvs-saas-prefill-job",
              JSON.stringify({
                job_url: args.job_url as string | undefined,
                job_description: args.job_description as string,
                title: args.title as string | undefined,
                company_name: args.company as string | undefined,
              }),
            );
            sessionStorage.setItem("cvs-saas-prefill-kind", "cover_letter");
          } catch {
            /* ignore */
          }
          window.location.hash = "#/cv/new";
          respond?.("opened-generator");
        }}
        onReject={() => respond?.("cancelled")}
      />
    ),
  });

  // --- Job match scorecard (display-only) ---------------------------------
  // The agent runs match_job_to_profile (MCP) server-side and then calls this
  // action with the result. We render the gauge + strengths/gaps inline; the
  // user can tap "Generar CV" to jump to the generator pre-filled.
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
    ] as any,
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

  // =========================================================================
  // Sprint B — Generic A2UI actions
  // =========================================================================

  // --- select_job_from_list -----------------------------------------------
  useCopilotAction({
    name: "select_job_from_list",
    description:
      "Show the user a list of jobs and let them pick one. Returns the selected job id.",
    parameters: [
      { name: "items", type: "object[]", required: true } as any,
      { name: "prompt", type: "string" },
    ] as any,
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

  // --- select_document_from_list ------------------------------------------
  useCopilotAction({
    name: "select_document_from_list",
    description:
      "Show the user a list of documents and let them pick one. Returns the selected document id.",
    parameters: [
      { name: "items", type: "object[]", required: true } as any,
      { name: "prompt", type: "string" },
    ] as any,
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
      { name: "items", type: "object[]", required: true } as any,
      { name: "title", type: "string" },
    ] as any,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <ListPreviewCard
        kind={(args.kind as PreviewKind) ?? "jobs"}
        items={(args.items as PreviewItem[]) ?? []}
        title={args.title as string | undefined}
      />
    ),
  });

  // --- propose_job_create -------------------------------------------------
  useCopilotAction({
    name: "propose_job_create",
    description:
      "Propose creating a new job tracker entry. The user confirms before we persist.",
    parameters: [
      { name: "title", type: "string" },
      { name: "company_name", type: "string" },
      { name: "url", type: "string" },
      { name: "description_raw", type: "string" },
    ] as any,
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
            qc.invalidateQueries({ queryKey: ["jobs"] });
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

  // --- propose_job_status_change ------------------------------------------
  useCopilotAction({
    name: "propose_job_status_change",
    description:
      "Propose moving a job to a different status (kanban transition).",
    parameters: [
      { name: "job_id", type: "string", required: true },
      { name: "new_status", type: "string", required: true },
      { name: "job_title", type: "string" },
      { name: "company", type: "string" },
    ] as any,
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
              qc.invalidateQueries({ queryKey: ["jobs"] });
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

  // --- propose_autopilot_run ----------------------------------------------
  // Lets the agent kick off the autopilot flow. We confirm here and then
  // redirect to JobsPage which opens the AutopilotRunner with prefs.
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
    ] as any,
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
          try {
            sessionStorage.setItem(
              "cvs-saas-autopilot-launch",
              JSON.stringify({
                job_id: args.job_id,
                template: args.suggested_template,
                language: args.suggested_language,
                tone: args.suggested_tone,
              }),
            );
          } catch {
            /* ignore */
          }
          window.location.hash = "#/jobs";
          respond?.(JSON.stringify({ ok: true, launched: true }));
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  // --- propose_cv_regenerate ----------------------------------------------
  useCopilotAction({
    name: "propose_cv_regenerate",
    description:
      "Propose regenerating an existing document with new template/language/tone.",
    parameters: [
      { name: "document_id", type: "string", required: true },
      { name: "template_override", type: "string" },
      { name: "language_override", type: "string" },
      { name: "tone_override", type: "string" },
      { name: "rationale", type: "string" },
    ] as any,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <ConfirmCard
        actionLabel="Regenerar"
        target="Documento"
        description={(args.rationale as string) ?? undefined}
        payload={{
          plantilla: args.template_override,
          idioma: args.language_override,
          tono: args.tone_override,
        }}
        confirmLabel="Abrir generador"
        onConfirm={() => {
          // We send the user to the generator with prefilled overrides; the
          // actual regeneration happens there with the existing flow.
          try {
            sessionStorage.setItem(
              "cvs-saas-cv-regenerate",
              JSON.stringify({
                document_id: args.document_id,
                template: args.template_override,
                language: args.language_override,
                tone: args.tone_override,
              }),
            );
          } catch {
            /* ignore */
          }
          window.location.hash = "#/cv/new";
          respond?.(JSON.stringify({ ok: true, redirected: true }));
        }}
        onCancel={() => respond?.(JSON.stringify({ cancelled: true }))}
      />
    ),
  });

  // --- propose_preferences_update -----------------------------------------
  useCopilotAction({
    name: "propose_preferences_update",
    description:
      "Propose patching the user's career preferences. Granular patches (1-3 fields).",
    parameters: [
      { name: "patch", type: "object", required: true } as any,
      { name: "rationale", type: "string" },
    ] as any,
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
              qc.invalidateQueries({ queryKey: ["universe", "preferences"] });
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
  // Generic gate. The agent's tool result is just the user's decision; the
  // actual destructive operation is the agent's next step server-side.
  useCopilotAction({
    name: "confirm_destructive",
    description:
      "Generic confirm gate for any action that requires explicit user approval before it runs.",
    parameters: [
      { name: "action_label", type: "string", required: true },
      { name: "target", type: "string", required: true },
      { name: "payload", type: "object" } as any,
      { name: "tone", type: "string" },
    ] as any,
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

  // --- set_chat_focus (display-less, fires shared state update) -----------
  useCopilotAction({
    name: "set_chat_focus",
    description:
      "Signal which entity the agent is currently reasoning about; the frontend uses this to highlight / pre-select it.",
    parameters: [
      { name: "entity", type: "string", required: true },
      { name: "id", type: "string", required: true },
      { name: "meta", type: "object" } as any,
    ] as any,
    handler: async (args: Record<string, unknown>) => {
      useChatState.getState().setFocus({
        entity: (args.entity as FocusEntity) ?? null,
        id: (args.id as string) ?? null,
        meta: (args.meta as Record<string, unknown>) ?? null,
      });
      return { ok: true };
    },
  });

  // --- present_graph_view (display-less, drives the universe graph lens) ---
  useCopilotAction({
    name: "present_graph_view",
    description:
      "Switch the universe graph lens to a mode (focus|cluster|timeline|ontology_overlay) optionally centred on an entity.",
    parameters: [
      { name: "mode", type: "string", required: true },
      { name: "focus_entity_id", type: "string" },
      { name: "depth", type: "number" },
    ] as any,
    handler: async (args: Record<string, unknown>) => {
      const mode = (args.mode as GraphLensMode) ?? "cluster";
      useGraphLensState.getState().setLens({
        mode,
        focusEntityId: (args.focus_entity_id as string) ?? null,
        depth: args.depth !== undefined ? Number(args.depth) : undefined,
      });
      return { ok: true, mode };
    },
  });

  // --- present_document_preview (display-only) ----------------------------
  useCopilotAction({
    name: "present_document_preview",
    description:
      "Render an inline preview of a generated document with collapsible sections.",
    available: "frontend",
    parameters: [
      { name: "document_id", type: "string", required: true },
      { name: "offer_regenerate", type: "boolean" },
    ] as any,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <DocumentPreviewCard
        documentId={args.document_id as string}
        onRegenerate={
          args.offer_regenerate
            ? () => {
                window.location.hash = "#/cv/new";
              }
            : undefined
        }
      />
    ),
  });

  // --- present_progress (display-only) ------------------------------------
  useCopilotAction({
    name: "present_progress",
    description:
      "Display-only progress card for a long-running task (steps + state).",
    available: "frontend",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "state", type: "string", required: true },
      { name: "steps", type: "object[]", required: true } as any,
      { name: "detail", type: "string" },
      { name: "error_message", type: "string" },
    ] as any,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <ProgressCard
        title={(args.title as string) ?? "Tarea"}
        state={((args.state as string) ?? "running") as "running" | "done" | "error"}
        steps={(args.steps as Parameters<typeof ProgressCard>[0]["steps"]) ?? []}
        detail={args.detail as string | undefined}
        errorMessage={args.error_message as string | undefined}
      />
    ),
  });

  // --- present_widget (display-only, pushes to WidgetPane) ----------------
  // Agent invokes this AFTER a read-only MCP tool (list_skills, list_certs,
  // get_experience…) to surface the result as a widget in the right pane.
  // The action body in chat is a tiny passive marker — the widget itself
  // renders elsewhere via the zustand store.
  useCopilotAction({
    name: "present_widget",
    description:
      "Render a widget in the right-side widget pane. Use this when the user asks to VIEW / SUMMARIZE structured insight from their universe. Call the relevant read-only tool first, then invoke this with kind + title + data. Supported kinds: goals_progress, interview_qa, tech_radar, agent_patterns, signal_coverage, document_preview, job_match, cloud_coverage, data_stack_topology, security_posture, architecture_patterns, portfolio_radar, learning_trajectory.",
    available: "frontend",
    parameters: [
      { name: "kind", type: "string", required: true },
      { name: "title", type: "string", required: true },
      { name: "data", type: "object", required: true } as any,
    ] as any,
    render: ({ args }: { args: Record<string, unknown> }) => (
      <PresentWidgetMarker
        kind={args.kind as WidgetKind}
        title={args.title as string}
        data={(args.data as Record<string, unknown>) ?? {}}
      />
    ),
  });

  // --- upload_document_inline ---------------------------------------------
  useCopilotAction({
    name: "upload_document_inline",
    description:
      "Open an inline upload dropzone in the chat so the user can drop a PDF/image without leaving the conversation.",
    parameters: [
      { name: "purpose", type: "string", required: true },
      { name: "accept", type: "string" },
      { name: "max_bytes", type: "number" },
    ] as any,
    renderAndWaitForResponse: ({
      args,
      respond,
    }: {
      args: Record<string, unknown>;
      respond?: (s: string) => void;
    }) => (
      <UploadInlineCard
        purpose={(args.purpose as string) ?? "Subir archivo"}
        accept={(args.accept as string) ?? "application/pdf"}
        maxBytes={(args.max_bytes as number) ?? 10 * 1024 * 1024}
        onComplete={(payload) => respond?.(JSON.stringify(payload))}
        onCancel={() => respond?.(JSON.stringify({ uploaded: false, cancelled: true }))}
      />
    ),
  });

  // --- Post-write feedback (DiffCard for last merge/created/suggested) ----
  // Rendered inline outside the chat surface so the user gets a tangible
  // "the engine merged X" cue right after a confirmation. The card stays
  // until the next outcome replaces it; the agent's text response covers
  // the in-chat acknowledgement.
  if (lastOutcome) {
    return (
      <div className="fixed bottom-4 right-4 z-30 pointer-events-none">
        <div className="pointer-events-auto">
          <DiffCard
            title={`${lastOutcome.kind}`}
            diffs={lastOutcome.resp.diffs}
            status={lastOutcome.resp.status}
          />
        </div>
      </div>
    );
  }
  return null;
}

/**
 * Tiny passive marker rendered in the chat stream when the agent emits
 * `present_widget`. The actual widget renders in the WidgetPane via zustand.
 * Pushing to the store happens once on mount; further renders are a no-op.
 */
function PresentWidgetMarker({
  kind,
  title,
  data,
}: {
  kind: WidgetKind;
  title: string;
  data: Record<string, unknown>;
}) {
  useEffect(() => {
    useChatState.getState().addWidget({ kind, title, data });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="text-xs text-stone italic mt-1">
      → Añadí <span className="font-medium text-ink/80">"{title}"</span> al panel
    </div>
  );
}
