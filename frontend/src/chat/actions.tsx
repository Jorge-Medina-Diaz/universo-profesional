/**
 * HITL CopilotKit actions: the agent proposes; the user confirms.
 *
 * Each action ships **without** a `handler` — that triggers the HITL flow where
 * the `render` prop is responsible for both displaying the proposal and calling
 * `respond()` once the user has confirmed/edited/rejected. The actual write to
 * the universe happens INSIDE the render callback through our regular REST API.
 *
 * Acceptable arguments map 1:1 to the MCP tool schemas — meaning the same
 * structured payload works whether the user came via web or via Claude Code.
 */
import { useCopilotAction } from "@copilotkit/react-core";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { universe } from "@/shared/api";
import { integrations, liveProfile } from "@/shared/api-extra";

interface CardProps {
  title: string;
  details: Record<string, unknown>;
  pending: boolean;
  onConfirm: () => void | Promise<void>;
  onReject: () => void;
  onEdit?: (key: string, value: string) => void;
  ctaLabel?: string;
}

function EntryCard({ title, details, pending, onConfirm, onReject, ctaLabel = "Añadir" }: CardProps) {
  const visible = Object.entries(details).filter(
    ([, v]) => v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0),
  );
  return (
    <div className="rounded-lg border border-brand-200 bg-brand-50/30 p-3 my-2 max-w-md">
      <h4 className="font-semibold text-sm mb-2">{title}</h4>
      <dl className="text-xs grid grid-cols-3 gap-y-1 mb-3">
        {visible.map(([k, v]) => (
          <DefRow key={k} k={k} v={v} />
        ))}
      </dl>
      <div className="flex gap-2">
        <button
          disabled={pending}
          onClick={onConfirm}
          className="bg-brand-600 hover:bg-brand-700 text-white rounded px-3 py-1 text-xs font-medium disabled:opacity-50"
        >
          {pending ? "Guardando…" : ctaLabel}
        </button>
        <button
          onClick={onReject}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 rounded px-3 py-1 text-xs"
        >
          Descartar
        </button>
      </div>
    </div>
  );
}

function DefRow({ k, v }: { k: string; v: unknown }) {
  let display: string;
  if (Array.isArray(v)) display = v.join(", ");
  else if (typeof v === "object" && v) display = JSON.stringify(v);
  else display = String(v);
  return (
    <>
      <dt className="text-gray-500 font-medium">{k}</dt>
      <dd className="col-span-2">{display}</dd>
    </>
  );
}

export function UniverseActions() {
  const qc = useQueryClient();
  const [savingKey, setSavingKey] = useState<string | null>(null);

  // --- Propose ENTRY (one HITL action per entity kind) ---

  useCopilotAction({
    name: "proposeExperienceEntry",
    description: "Propose adding a work experience entry. User must confirm.",
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
    render: ({ status, args, respond }) => (
      <EntryCard
        title={`Experiencia: ${args.role ?? "?"} @ ${args.organization ?? "?"}`}
        details={args as Record<string, unknown>}
        pending={savingKey === "experience"}
        onConfirm={async () => {
          setSavingKey("experience");
          try {
            await universe.add("experience", args as Record<string, unknown>);
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.("Experience added.");
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Rejected.")}
      />
    ),
  });

  useCopilotAction({
    name: "proposeEducationEntry",
    description: "Propose adding an education entry. User must confirm.",
    parameters: [
      { name: "institution", type: "string", required: true },
      { name: "degree", type: "string" },
      { name: "field_of_study", type: "string" },
      { name: "start_date", type: "string" },
      { name: "end_date", type: "string" },
      { name: "description", type: "string" },
    ],
    render: ({ args, respond }) => (
      <EntryCard
        title={`Educación: ${args.degree ?? ""} ${args.institution ?? ""}`}
        details={args as Record<string, unknown>}
        pending={savingKey === "education"}
        onConfirm={async () => {
          setSavingKey("education");
          try {
            await universe.add("education", args as Record<string, unknown>);
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.("Education added.");
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Rejected.")}
      />
    ),
  });

  useCopilotAction({
    name: "proposeProjectEntry",
    description: "Propose adding a project entry.",
    parameters: [
      { name: "name", type: "string", required: true },
      { name: "description", type: "string" },
      { name: "url", type: "string" },
      { name: "tech_stack", type: "string[]" },
      { name: "highlights", type: "string[]" },
    ],
    render: ({ args, respond }) => (
      <EntryCard
        title={`Proyecto: ${args.name ?? "?"}`}
        details={args as Record<string, unknown>}
        pending={savingKey === "project"}
        onConfirm={async () => {
          setSavingKey("project");
          try {
            await universe.add("project", args as Record<string, unknown>);
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.("Project added.");
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Rejected.")}
      />
    ),
  });

  useCopilotAction({
    name: "proposeSkillEntry",
    description: "Propose adding a skill.",
    parameters: [
      { name: "name", type: "string", required: true },
      { name: "category", type: "string" },
      { name: "level", type: "string" },
      { name: "years", type: "number" },
    ],
    render: ({ args, respond }) => (
      <EntryCard
        title={`Skill: ${args.name ?? "?"}`}
        details={args as Record<string, unknown>}
        pending={savingKey === "skill"}
        onConfirm={async () => {
          setSavingKey("skill");
          try {
            await universe.add("skill", { category: "hard", ...(args as Record<string, unknown>) });
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.("Skill added.");
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Rejected.")}
      />
    ),
  });

  // --- Propose GitHub sync ---

  useCopilotAction({
    name: "proposeGithubSync",
    description: "Suggest pulling the user's GitHub profile (repos, languages, pinned). HITL — user confirms.",
    parameters: [],
    render: ({ respond }) => (
      <EntryCard
        title="Importar perfil de GitHub"
        details={{
          contenido: "repos · lenguajes · pinned · contributions · orgs",
          duracion: "~10-20 s",
          irreversible: "no (puedes editar/borrar entries individuales después)",
        }}
        pending={savingKey === "gh-sync"}
        ctaLabel="Sincronizar ahora"
        onConfirm={async () => {
          setSavingKey("gh-sync");
          try {
            const r = await integrations.github.sync();
            qc.invalidateQueries({ queryKey: ["universe"] });
            respond?.(`Sync ok — ${JSON.stringify(r)}`);
          } catch (e) {
            respond?.(`Sync falló: ${(e as Error).message}`);
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Sync rechazado.")}
      />
    ),
  });

  // --- Apply a suggestion ---

  useCopilotAction({
    name: "applySuggestion",
    description: "Apply (accept or reject) a stored suggestion by id.",
    parameters: [
      { name: "suggestion_id", type: "string", required: true },
      { name: "action", type: "string", required: true, enum: ["accept", "reject"] },
    ],
    render: ({ args, respond }) => (
      <EntryCard
        title={`Sugerencia ${args.action ?? "accept"}`}
        details={{ id: args.suggestion_id }}
        pending={savingKey === "sug"}
        ctaLabel={(args.action as string) === "reject" ? "Rechazar" : "Aceptar"}
        onConfirm={async () => {
          setSavingKey("sug");
          try {
            await liveProfile.suggestions.act(
              String(args.suggestion_id),
              (args.action as "accept" | "reject") ?? "accept",
            );
            qc.invalidateQueries({ queryKey: ["suggestions"] });
            respond?.("Done.");
          } finally {
            setSavingKey(null);
          }
        }}
        onReject={() => respond?.("Cancelled.")}
      />
    ),
  });

  return null;
}
