/**
 * ProposalCard — rich HITL card for entity proposals with inline editing.
 *
 * Receives a structured proposal payload (injected server-side into the
 * AG-UI tool-call event) and renders a rich card with confirm / edit /
 * reject actions.  Editing happens inline; the resolution endpoint handles
 * confirm, modify and reject flows.
 */
import { useState } from "react";
import {
  Briefcase,
  GraduationCap,
  FolderGit,
  Zap,
  Award,
  Target,
  Check,
  X,
  Pencil,
} from "lucide-react";
import { Badge, Button, ChatMessageMotion, Input, Textarea, cn, toast } from "@/ui";
import { resolveProposal } from "../actions/shared";
import type { UpsertResponse } from "../actions/types";

export type EntityType =
  | "experience"
  | "education"
  | "project"
  | "skill"
  | "certification"
  | "goal";

interface ProposalPayload {
  proposal_id: string;
  entity_type: EntityType;
  entity_data: Record<string, unknown>;
  action: string;
  confidence: number;
  reason: string;
}

export interface ProposalCardProps {
  payload: ProposalPayload;
  pending?: boolean;
  onResolved?: (result: { action: string; response: UpsertResponse }) => void;
}

const ENTITY_META: Record<
  EntityType,
  { label: string; icon: typeof Briefcase; tone: "leaf" | "sunbeam" | "stone" }
> = {
  experience: { label: "Experiencia", icon: Briefcase, tone: "leaf" },
  education: { label: "Educación", icon: GraduationCap, tone: "leaf" },
  project: { label: "Proyecto", icon: FolderGit, tone: "sunbeam" },
  skill: { label: "Skill", icon: Zap, tone: "sunbeam" },
  certification: { label: "Certificación", icon: Award, tone: "leaf" },
  goal: { label: "Meta", icon: Target, tone: "sunbeam" },
};

function entityTitle(payload: ProposalPayload): string {
  const d = payload.entity_data;
  switch (payload.entity_type) {
    case "experience":
      return `${(d.role as string) || "Experiencia"} @ ${(d.organization as string) || "?"}`;
    case "education":
      return `${(d.degree as string) || (d.field_of_study as string) || "Educación"} — ${(d.institution as string) || "?"}`;
    case "project":
      return (d.name as string) || "Proyecto";
    case "skill":
      return (d.name as string) || "Skill";
    case "certification":
      return (d.name as string) || "Certificación";
    case "goal":
      return (d.title as string) || "Meta";
    default:
      return "Propuesta";
  }
}

function visibleFields(
  payload: ProposalPayload,
): Array<[string, unknown]> {
  const skip = new Set([
    "proposal_id",
    "entity_type",
    "action",
    "confidence",
    "reason",
  ]);
  return Object.entries(payload.entity_data).filter(([k, v]) => {
    if (skip.has(k)) return false;
    if (v === null || v === undefined || v === "") return false;
    if (Array.isArray(v) && v.length === 0) return false;
    return true;
  });
}

export function ProposalCard({
  payload,
  pending: pendingProp = false,
  onResolved,
}: ProposalCardProps) {
  const [mode, setMode] = useState<"view" | "edit" | "success" | "rejected">("view");
  const [pending, setPending] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    visibleFields(payload).forEach(([k, v]) => {
      init[k] = Array.isArray(v) ? v.join(", ") : String(v ?? "");
    });
    return init;
  });

  const meta = ENTITY_META[payload.entity_type] ?? {
    label: "Propuesta",
    icon: Briefcase,
    tone: "stone",
  };
  const Icon = meta.icon;

  const handleConfirm = async () => {
    setPending(true);
    try {
      const resp = await resolveProposal(payload.proposal_id, "confirm");
      setMode("success");
      onResolved?.({ action: "confirm", response: resp });
    } catch (e) {
      toast.error(
        "No se pudo guardar la propuesta",
        e instanceof Error ? e.message : undefined,
      );
    } finally {
      setPending(false);
    }
  };

  const handleModify = async () => {
    setPending(true);
    try {
      const modified: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(edits)) {
        const orig = payload.entity_data[k];
        if (Array.isArray(orig)) {
          modified[k] = v.split(",").map((s) => s.trim()).filter(Boolean);
        } else if (typeof orig === "number") {
          const n = Number(v);
          modified[k] = Number.isNaN(n) ? v : n;
        } else if (typeof orig === "boolean") {
          modified[k] = v.toLowerCase() === "true";
        } else {
          modified[k] = v;
        }
      }
      const resp = await resolveProposal(payload.proposal_id, "modify", modified);
      setMode("success");
      onResolved?.({ action: "modify", response: resp });
    } catch (e) {
      toast.error(
        "No se pudieron guardar los cambios",
        e instanceof Error ? e.message : undefined,
      );
    } finally {
      setPending(false);
    }
  };

  const handleReject = async () => {
    setPending(true);
    try {
      const resp = await resolveProposal(payload.proposal_id, "reject");
      setMode("rejected");
      onResolved?.({ action: "reject", response: resp });
    } catch (e) {
      toast.error(
        "No se pudo rechazar la propuesta",
        e instanceof Error ? e.message : undefined,
      );
    } finally {
      setPending(false);
    }
  };

  if (mode === "success") {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface/60 px-4 py-3 my-3 max-w-md border border-ink/[0.05] flex items-center gap-2.5">
          <span className="grid place-items-center h-6 w-6 rounded-full bg-leaf/15 text-leaf-ink shrink-0">
            <Check size={13} strokeWidth={2.5} />
          </span>
          <div className="min-w-0">
            <span className="text-xs text-stone">Guardado</span>
            <span className="text-sm text-ink font-medium truncate">
              {" "}
              · {entityTitle(payload)}
            </span>
          </div>
          <Badge tone={meta.tone} size="sm" className="ml-auto shrink-0">
            {meta.label}
          </Badge>
        </div>
      </ChatMessageMotion>
    );
  }

  if (mode === "rejected") {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface/60 px-4 py-3 my-3 max-w-md border border-ink/[0.05] flex items-center gap-2.5">
          <span className="grid place-items-center h-6 w-6 rounded-full bg-ink/[0.06] text-stone shrink-0">
            <X size={13} strokeWidth={2.5} />
          </span>
          <div className="min-w-0">
            <span className="text-xs text-stone">Descartado</span>
            <span className="text-sm text-ink font-medium truncate">
              {" "}
              · {entityTitle(payload)}
            </span>
          </div>
          <Badge tone="stone" size="sm" className="ml-auto shrink-0">
            {meta.label}
          </Badge>
        </div>
      </ChatMessageMotion>
    );
  }

  const isEditing = mode === "edit";

  return (
    <ChatMessageMotion>
      <div
        role="group"
        aria-label={`Propuesta de ${meta.label}: ${entityTitle(payload)}`}
        className="rounded-card bg-surface my-3 max-w-lg shadow-soft border border-ink/[0.06] overflow-hidden"
      >
        {/* Header */}
        <header className="flex items-start gap-3 px-5 pt-5 pb-3">
          <span
            aria-hidden
            className={cn(
              "inline-flex items-center justify-center w-10 h-10 rounded-full shrink-0",
              meta.tone === "leaf"
                ? "bg-leaf-soft text-leaf-ink"
                : meta.tone === "sunbeam"
                  ? "bg-sunbeam-soft text-sunbeam-ink"
                  : "bg-canvas text-ink",
            )}
          >
            <Icon size={18} />
          </span>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge tone={meta.tone} size="sm">
                {meta.label}
              </Badge>
              <Badge tone="stone" size="sm">
                {Math.round((payload.confidence || 0) * 100)}% confianza
              </Badge>
            </div>
            <h4 className="font-medium text-base text-ink leading-tight">
              {entityTitle(payload)}
            </h4>
            {payload.reason && (
              <p className="text-xs text-stone leading-relaxed">{payload.reason}</p>
            )}
          </div>
        </header>

        {/* Fields */}
        <div className="px-5 pb-3">
          {isEditing ? (
            <div className="flex flex-col gap-2.5">
              {visibleFields(payload).map(([k, v]) => (
                <div key={k}>
                  <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
                    {k.replace(/_/g, " ")}
                  </label>
                  {typeof v === "string" && (v as string).length > 60 ? (
                    <Textarea
                      value={edits[k] ?? ""}
                      onChange={(e) =>
                        setEdits((prev) => ({ ...prev, [k]: e.target.value }))
                      }
                      rows={2}
                    />
                  ) : (
                    <Input
                      value={edits[k] ?? ""}
                      onChange={(e) =>
                        setEdits((prev) => ({ ...prev, [k]: e.target.value }))
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <dl className="text-xs space-y-1.5">
              {visibleFields(payload).map(([k, v]) => (
                <div
                  key={k}
                  className="grid grid-cols-[110px_1fr] gap-3 items-baseline"
                >
                  <dt className="text-stone font-medium capitalize truncate" title={k}>
                    {k.replace(/_/g, " ")}
                  </dt>
                  <dd className="text-ink break-words">
                    {Array.isArray(v) ? v.join(", ") : String(v)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        {/* Footer actions */}
        <footer className="flex items-center gap-2 px-5 py-4 bg-canvas/40 border-t border-ink/[0.05]">
          {isEditing ? (
            <>
              <Button
                size="sm"
                loading={pending}
                onClick={() => void handleModify()}
                leadingIcon={!pending && <Check size={14} strokeWidth={2.5} />}
              >
                Guardar cambios
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setMode("view")}>
                Cancelar edición
              </Button>
            </>
          ) : (
            <>
              <Button
                size="sm"
                loading={pending || pendingProp}
                onClick={() => void handleConfirm()}
                leadingIcon={
                  !(pending || pendingProp) && <Check size={14} strokeWidth={2.5} />
                }
              >
                Confirmar
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setMode("edit")}
                leadingIcon={<Pencil size={14} />}
                disabled={pending || pendingProp}
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void handleReject()}
                leadingIcon={<X size={14} />}
                disabled={pending || pendingProp}
              >
                Rechazar
              </Button>
            </>
          )}
        </footer>
      </div>
    </ChatMessageMotion>
  );
}

/** Terminal chip rendered after a proposal is resolved via the action loop. */
export function ResolvedProposalChip({
  payload,
  result,
}: {
  payload: ProposalPayload;
  result?: string;
}) {
  const rejected = !!result && /rejected/i.test(result);
  const errored = !!result && /^error/i.test(result.trim());
  const meta = ENTITY_META[payload.entity_type] ?? {
    label: "Propuesta",
    icon: Briefcase,
    tone: "stone",
  };
  const Icon = errored || rejected ? X : Check;
  const tone = errored ? "stone" : rejected ? "stone" : "leaf";
  const label = errored ? "No se pudo guardar" : rejected ? "Descartado" : "Guardado";
  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface/60 px-4 py-3 my-3 max-w-md border border-ink/[0.05] flex items-center gap-2.5">
        <span
          className={cn(
            "grid place-items-center h-6 w-6 rounded-full shrink-0",
            tone === "leaf" ? "bg-leaf/15 text-leaf-ink" : "bg-ink/[0.06] text-stone",
          )}
        >
          <Icon size={13} strokeWidth={2.5} />
        </span>
        <div className="min-w-0">
          <span className="text-xs text-stone">{label}</span>
          {!errored && !rejected && (
            <span className="text-sm text-ink font-medium truncate">
              {" "}
              · {entityTitle(payload)}
            </span>
          )}
        </div>
        {!errored && !rejected && (
          <Badge tone={meta.tone} size="sm" className="ml-auto shrink-0">
            {meta.label}
          </Badge>
        )}
      </div>
    </ChatMessageMotion>
  );
}
