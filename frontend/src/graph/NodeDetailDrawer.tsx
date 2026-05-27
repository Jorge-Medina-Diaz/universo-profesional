/**
 * NodeDetailDrawer — the rich panel that opens when a graph node is selected.
 *
 * Lazy-loads the entity's full content (per-kind list endpoint), its graph
 * neighbours, and any documents it sourced. Neighbours are clickable and
 * navigate the graph (parent re-selects → camera animates). The detail content
 * is rendered from a per-kind field spec so each kind shows what matters.
 *
 * Edit mode: every non-document kind can be edited in-place. Changes are sent
 * via PATCH /api/v1/universe/{kind}/{id} and relevant queries are invalidated
 * so the graph + lists refresh automatically.
 */
import { useMemo, useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUpRight, MessageSquare, Pencil, X } from "lucide-react";
import { Badge, Button, Input, Textarea, Field, ChipInput, Select, toast } from "@/ui";
import { KIND_COLORS, KIND_LABELS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import { iconFor } from "./nodeIcons";
import {
  kindHasDetail,
  useEntityDetail,
  type EntityRow,
} from "./entityDetail";
import { universe } from "@/shared/api";
import type { GraphSnapshot } from "./api";
import type { GraphSelection } from "./GraphView";
import { queryKeys } from "@/shared/queryKeys";

type FieldType = "text" | "date" | "range" | "chips" | "bullets" | "link" | "number";
interface FieldSpec {
  key: string;
  label: string;
  type?: FieldType;
}

// Title field + the notable fields to surface, per kind.
const TITLE_KEY: Record<string, string> = {
  experience: "role",
  project: "name",
  skill: "name",
  education: "degree",
  certification: "name",
  course: "title",
  language: "name",
  achievement: "title",
  interest: "name",
};

const FIELD_SPECS: Record<string, FieldSpec[]> = {
  experience: [
    { key: "organization", label: "Organización" },
    { key: "__range", label: "Periodo", type: "range" },
    { key: "seniority_level", label: "Seniority" },
    { key: "employment_type", label: "Contrato" },
    { key: "modality", label: "Modalidad" },
    { key: "industry_sector", label: "Sector" },
    { key: "description", label: "Descripción" },
    { key: "highlights", label: "Hitos", type: "bullets" },
    { key: "competences", label: "Competencias", type: "chips" },
    { key: "url", label: "Enlace", type: "link" },
  ],
  project: [
    { key: "role", label: "Rol" },
    { key: "project_type", label: "Tipo" },
    { key: "status", label: "Estado" },
    { key: "__range", label: "Periodo", type: "range" },
    { key: "description", label: "Descripción" },
    { key: "tech_stack", label: "Stack", type: "chips" },
    { key: "highlights", label: "Hitos", type: "bullets" },
    { key: "impact", label: "Impacto" },
    { key: "domain_tags", label: "Dominios", type: "chips" },
    { key: "url", label: "Enlace", type: "link" },
  ],
  skill: [
    { key: "category", label: "Categoría" },
    { key: "level", label: "Nivel" },
    { key: "years", label: "Años", type: "number" },
    { key: "last_used_year", label: "Último uso", type: "number" },
  ],
  education: [
    { key: "institution", label: "Institución" },
    { key: "field_of_study", label: "Área" },
    { key: "__range", label: "Periodo", type: "range" },
    { key: "gpa", label: "Nota", type: "number" },
    { key: "description", label: "Descripción" },
    { key: "highlights", label: "Hitos", type: "bullets" },
    { key: "url", label: "Enlace", type: "link" },
  ],
  certification: [
    { key: "issuer", label: "Emisor" },
    { key: "issued_on", label: "Emitida", type: "date" },
    { key: "expires_on", label: "Caduca", type: "date" },
    { key: "credential_id", label: "ID credencial" },
    { key: "verification_url", label: "Verificar", type: "link" },
  ],
  course: [
    { key: "platform", label: "Plataforma" },
    { key: "started_on", label: "Inicio", type: "date" },
    { key: "completed_on", label: "Fin", type: "date" },
    { key: "duration_hours", label: "Horas" },
    { key: "certificate_url", label: "Certificado", type: "link" },
  ],
  language: [
    { key: "level", label: "Nivel (CEFR)" },
    { key: "code", label: "Código" },
    { key: "certification", label: "Certificación" },
  ],
  achievement: [
    { key: "achieved_on", label: "Fecha", type: "date" },
    { key: "context", label: "Contexto" },
    { key: "description", label: "Descripción" },
    { key: "evidence_url", label: "Evidencia", type: "link" },
  ],
  interest: [{ key: "description", label: "Descripción" }],
};

const SELECT_OPTIONS: Record<string, { value: string; label: string }[]> = {
  seniority_level: [
    { value: "junior", label: "Junior" },
    { value: "mid", label: "Mid" },
    { value: "senior", label: "Senior" },
    { value: "lead", label: "Lead" },
    { value: "staff", label: "Staff" },
    { value: "principal", label: "Principal" },
  ],
  employment_type: [
    { value: "full-time", label: "Tiempo completo" },
    { value: "part-time", label: "Medio tiempo" },
    { value: "contract", label: "Contrato" },
    { value: "freelance", label: "Freelance" },
    { value: "internship", label: "Prácticas" },
  ],
  modality: [
    { value: "remote", label: "Remoto" },
    { value: "hybrid", label: "Híbrido" },
    { value: "on-site", label: "Presencial" },
  ],
  level: [
    { value: "basic", label: "Básico" },
    { value: "intermediate", label: "Intermedio" },
    { value: "high", label: "Avanzado" },
    { value: "expert", label: "Experto" },
  ],
  project_type: [
    { value: "personal", label: "Personal" },
    { value: "professional", label: "Profesional" },
    { value: "open-source", label: "Open Source" },
    { value: "academic", label: "Académico" },
  ],
  status: [
    { value: "active", label: "Activo" },
    { value: "completed", label: "Completado" },
    { value: "archived", label: "Archivado" },
    { value: "paused", label: "Pausado" },
  ],
  category: [
    { value: "hard", label: "Hard skill" },
    { value: "soft", label: "Soft skill" },
    { value: "tool", label: "Herramienta" },
  ],
};

function fmtDate(v: unknown): string {
  if (!v) return "";
  const d = new Date(String(v));
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleDateString("es-ES", { month: "short", year: "numeric" });
}

function toDateInputValue(v: unknown): string {
  if (!v) return "";
  const s = String(v);
  // Accept ISO strings or plain YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  return "";
}

function asArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x)).filter(Boolean);
  return [];
}

function computeDelta(original: EntityRow, draft: Record<string, unknown>): Record<string, unknown> {
  const delta: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(draft)) {
    const orig = original[key];
    if (JSON.stringify(value) !== JSON.stringify(orig)) {
      delta[key] = value;
    }
  }
  return delta;
}

function FieldRead({ spec, row }: { spec: FieldSpec; row: EntityRow }) {
  let value: unknown = row[spec.key];
  if (spec.type === "range") {
    const start = fmtDate(row.start_date);
    const end = row.is_current ? "Actual" : fmtDate(row.end_date);
    value = [start, end].filter(Boolean).join(" — ");
  }
  if (value === null || value === undefined || value === "") return null;
  if ((spec.type === "chips" || spec.type === "bullets") && asArray(value).length === 0) return null;

  return (
    <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
      <dt className="text-xs font-medium text-stone pt-0.5">{spec.label}</dt>
      <dd className="text-sm text-ink min-w-0">
        {spec.type === "chips" ? (
          <div className="flex flex-wrap gap-1">
            {asArray(value).map((c, i) => (
              <span key={i} className="rounded-full bg-ink/[0.05] px-2 py-0.5 text-xs text-ink/80">
                {c}
              </span>
            ))}
          </div>
        ) : spec.type === "bullets" ? (
          <ul className="space-y-1">
            {asArray(value).map((c, i) => (
              <li key={i} className="flex gap-1.5">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-leaf" />
                <span className="leading-snug">{c}</span>
              </li>
            ))}
          </ul>
        ) : spec.type === "link" ? (
          <a
            href={String(value)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-leaf-ink hover:underline break-all"
          >
            {String(value).replace(/^https?:\/\//, "").slice(0, 40)}
            <ArrowUpRight size={12} />
          </a>
        ) : spec.type === "date" ? (
          fmtDate(value)
        ) : (
          <span className="break-words leading-snug">{String(value)}</span>
        )}
      </dd>
    </div>
  );
}

interface NeighborItem {
  id: string;
  kind: string;
  label: string;
  relation?: string;
}

export interface NodeDetailDrawerProps {
  selection: GraphSelection | null;
  /** Current graph snapshot — neighbours are derived from its edges. */
  snapshot?: GraphSnapshot | null;
  onClose: () => void;
  onNavigate: (sel: GraphSelection) => void;
  onChatFocus: (id: string, kind: string, label: string) => void;
}

export function NodeDetailDrawer({
  selection,
  snapshot,
  onClose,
  onNavigate,
  onChatFocus,
}: NodeDetailDrawerProps) {
  const open = !!selection;
  const kind = selection?.kind ?? null;
  const id = selection?.id ?? null;
  const { data, isLoading } = useEntityDetail(kind, id);
  const queryClient = useQueryClient();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const color = kind ? KIND_COLORS[kind] ?? DEFAULT_KIND_COLOR : DEFAULT_KIND_COLOR;
  const row = data?.row ?? null;
  const doc = data?.document ?? null;
  const specs = kind ? FIELD_SPECS[kind] ?? [] : [];
  const title =
    (row && kind && (row[TITLE_KEY[kind] ?? "name"] as string)) || selection?.label || "";
  const confidence = typeof row?.confidence === "number" ? Math.round(row.confidence * 100) : null;

  // Reset editing state when the selection changes or drawer closes.
  useEffect(() => {
    if (!open) setEditing(false);
  }, [open]);

  const saveMutation = useMutation({
    mutationFn: async ({
      kind,
      id,
      body,
    }: {
      kind: string;
      id: string;
      body: Record<string, unknown>;
    }) => {
      return universe.patch(kind, id, body);
    },
    onSuccess: (_, vars) => {
      toast.success("Guardado", "Los cambios se guardaron correctamente.");
      setEditing(false);
      queryClient.invalidateQueries({ queryKey: queryKeys.entity.detail(vars.kind, vars.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.graph.snapshot });
      queryClient.invalidateQueries({ queryKey: queryKeys.universe.summary });
      queryClient.invalidateQueries({ queryKey: queryKeys.trajectory.all });
    },
    onError: (err: Error) => {
      toast.error("No se pudo guardar", err.message || "Inténtalo de nuevo.");
    },
  });

  const startEditing = () => {
    if (!row) return;
    setDraft({ ...row });
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setDraft({});
  };

  const submitEditing = () => {
    if (!row || !kind || !id) return;
    const delta = computeDelta(row, draft);
    if (Object.keys(delta).length === 0) {
      setEditing(false);
      return;
    }
    saveMutation.mutate({ kind, id, body: delta });
  };

  const updateDraft = (key: string, value: unknown) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  // Neighbours come straight from the snapshot the graph already holds — real
  // names, no extra round-trip, reflects the agent-inferred relationships.
  const neighborList = useMemo<NeighborItem[]>(() => {
    if (!id || !snapshot) return [];
    const nodes = new Map(snapshot.nodes.map((n) => [n.key, n.attributes]));
    const out: NeighborItem[] = [];
    const seen = new Set<string>();
    for (const e of snapshot.edges) {
      const other: string | null =
        e.source === id ? e.target : e.target === id ? e.source : null;
      if (!other || other === id || seen.has(other)) continue;
      const attrs = nodes.get(other);
      if (!attrs) continue;
      seen.add(other);
      out.push({
        id: other,
        kind: String(attrs.kind ?? "entity"),
        label: String(attrs.label ?? other),
        relation: typeof e.attributes.edge_type === "string" ? e.attributes.edge_type : undefined,
      });
    }
    return out;
  }, [id, snapshot]);

  // Career pillar (Leiden community) the node belongs to, from the snapshot.
  const pillar = useMemo<string | null>(() => {
    if (!id || !snapshot) return null;
    const node = snapshot.nodes.find((n) => n.key === id);
    const p = node?.attributes.pillar;
    return typeof p === "string" && p ? p : null;
  }, [id, snapshot]);

  // Esc closes the inspector without blocking the graph (no backdrop).
  useEscapeKey(onClose, open);

  const editable = !!row && kind !== "document" && kind !== "interest" && kind !== null;

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          key="inspector"
          initial={{ x: 24, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 24, opacity: 0 }}
          transition={{ type: "spring", stiffness: 420, damping: 40 }}
          role="dialog"
          aria-modal="true"
          aria-label={`Ficha de ${title || "entidad"}`}
          className="node-inspector pointer-events-auto absolute right-4 top-4 z-30 flex max-h-[calc(100%-2rem)] w-[min(94%,360px)] flex-col overflow-hidden rounded-card border border-hairline shadow-float"
        >
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-start gap-3 bg-canvas/70 backdrop-blur px-5 pt-5 pb-4 border-b border-hairline">
              <span
                className="grid h-9 w-9 shrink-0 place-items-center rounded-full"
                style={{ backgroundColor: color }}
              >
                <img src={iconFor(kind ?? "")} alt="" className="h-4 w-4" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="eyebrow">{kind ? KIND_LABELS[kind] ?? kind : ""}</p>
                <h3 className="font-display text-[19px] leading-tight text-ink break-words">
                  {title}
                </h3>
              </div>
              <div className="flex items-center gap-1">
                {editable && !editing && (
                  <button
                    type="button"
                    aria-label="Editar"
                    onClick={startEditing}
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-stone hover:text-ink hover:bg-surface transition-colors"
                  >
                    <Pencil size={14} />
                  </button>
                )}
                <button
                  type="button"
                  aria-label="Cerrar"
                  onClick={onClose}
                  className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-stone hover:text-ink hover:bg-surface transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="px-5 py-4 space-y-5">
              {/* Meta chips */}
              {(confidence !== null || Boolean(row?.source) || Boolean(row?.is_current) || pillar) && (
                <div className="flex flex-wrap gap-1.5">
                  {pillar ? <Badge tone="leaf" size="sm">◆ {pillar}</Badge> : null}
                  {row?.is_current ? <Badge tone="leaf" size="sm">Actual</Badge> : null}
                  {confidence !== null ? (
                    <Badge tone="stone" size="sm">{confidence}% confianza</Badge>
                  ) : null}
                  {row?.source ? (
                    <Badge tone="stone" size="sm">{String(row.source)}</Badge>
                  ) : null}
                </div>
              )}

              {/* Body — read or edit */}
              {isLoading ? (
                <p className="text-sm text-stone">Cargando…</p>
              ) : doc ? (
                <DocumentBody doc={doc} />
              ) : row ? (
                editing ? (
                  <div className="space-y-3">
                    {specs.map((spec) => {
                      if (spec.key === "__range") {
                        return (
                          <div key="__range" className="space-y-3">
                            <Field label="Fecha inicio">
                              {(props) => (
                                <Input
                                  {...props}
                                  type="date"
                                  value={toDateInputValue(draft.start_date)}
                                  onChange={(e) => updateDraft("start_date", e.target.value)}
                                />
                              )}
                            </Field>
                            <Field label="Fecha fin">
                              {(props) => (
                                <Input
                                  {...props}
                                  type="date"
                                  value={toDateInputValue(draft.end_date)}
                                  onChange={(e) => updateDraft("end_date", e.target.value)}
                                />
                              )}
                            </Field>
                            <label className="flex items-center gap-2 text-sm text-ink cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!draft.is_current}
                                onChange={(e) => updateDraft("is_current", e.target.checked)}
                                className="h-4 w-4 rounded border-hairline"
                              />
                              Actual (sin fecha de fin)
                            </label>
                          </div>
                        );
                      }

                      const key = spec.key;
                      const val = draft[key];
                      const options = SELECT_OPTIONS[key];

                      if (options) {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <Select
                                {...props}
                                options={options}
                                value={String(val ?? "")}
                                onChange={(v) => updateDraft(key, v)}
                              />
                            )}
                          </Field>
                        );
                      }

                      if (spec.type === "date") {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <Input
                                {...props}
                                type="date"
                                value={toDateInputValue(val)}
                                onChange={(e) => updateDraft(key, e.target.value)}
                              />
                            )}
                          </Field>
                        );
                      }

                      if (spec.type === "chips" || spec.type === "bullets") {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <ChipInput
                                {...props}
                                value={asArray(val)}
                                onChange={(next) => updateDraft(key, next)}
                              />
                            )}
                          </Field>
                        );
                      }

                      if (spec.type === "link") {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <Input
                                {...props}
                                type="url"
                                value={String(val ?? "")}
                                onChange={(e) => updateDraft(key, e.target.value)}
                              />
                            )}
                          </Field>
                        );
                      }

                      if (spec.type === "number") {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <Input
                                {...props}
                                type="number"
                                value={String(val ?? "")}
                                onChange={(e) => {
                                  const v = e.target.value;
                                  if (v === "") return updateDraft(key, null);
                                  const n = Number(v);
                                  updateDraft(key, Number.isNaN(n) ? null : n);
                                }}
                              />
                            )}
                          </Field>
                        );
                      }

                      if (key === "description" || key === "impact") {
                        return (
                          <Field key={key} label={spec.label}>
                            {(props) => (
                              <Textarea
                                {...props}
                                value={String(val ?? "")}
                                onChange={(e) => updateDraft(key, e.target.value)}
                              />
                            )}
                          </Field>
                        );
                      }

                      return (
                        <Field key={key} label={spec.label}>
                          {(props) => (
                            <Input
                              {...props}
                              value={String(val ?? "")}
                              onChange={(e) => updateDraft(key, e.target.value)}
                            />
                          )}
                        </Field>
                      );
                    })}
                  </div>
                ) : (
                  <dl className="divide-y divide-hairline/60">
                    {specs.map((spec) => (
                      <FieldRead key={spec.key} spec={spec} row={row} />
                    ))}
                  </dl>
                )
              ) : !kindHasDetail(kind ?? "") ? (
                <p className="text-sm text-stone leading-relaxed">
                  Este nodo no tiene una ficha detallada todavía. Pregúntale al agente
                  para profundizar.
                </p>
              ) : null}

              {/* Neighbours — derived from the graph's own edges */}
              {!editing && neighborList.length > 0 && (
                <section>
                  <p className="eyebrow mb-2">
                    Conectado con <span className="text-stone/70">· {neighborList.length}</span>
                  </p>
                  <ul className="space-y-1">
                    {neighborList.slice(0, 10).map((n) => (
                      <li key={n.id}>
                        <button
                          type="button"
                          onClick={() => onNavigate({ id: n.id, kind: n.kind, label: n.label })}
                          aria-label={`Navegar a ${n.label}`}
                          className="group flex w-full items-center gap-2 rounded-btn px-2 py-1.5 text-left hover:bg-surface transition-colors"
                        >
                          <span
                            className="h-2 w-2 shrink-0 rounded-full"
                            style={{ backgroundColor: KIND_COLORS[n.kind] ?? DEFAULT_KIND_COLOR }}
                          />
                          <span className="truncate text-sm text-ink/80 group-hover:text-ink">
                            {n.label}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Actions */}
              {!editing && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {kind !== "document" && id ? (
                    <Button
                      size="sm"
                      leadingIcon={<MessageSquare size={14} />}
                      onClick={() => onChatFocus(id, kind ?? "entity", title)}
                    >
                      Hablar de esto
                    </Button>
                  ) : null}
                  {kind === "document" && id ? (
                    <Button
                      size="sm"
                      variant="outline"
                      leadingIcon={<ArrowUpRight size={14} />}
                      onClick={() => (window.location.hash = `#/documents/${id.replace(/^doc-/, "")}`)}
                    >
                      Abrir documento
                    </Button>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          {/* Edit footer */}
          {editing && (
            <div className="shrink-0 border-t border-hairline bg-canvas/80 backdrop-blur px-5 py-3 flex items-center justify-between gap-3">
              <Button
                size="sm"
                variant="ghost"
                onClick={cancelEditing}
                disabled={saveMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                onClick={submitEditing}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? "Guardando…" : "Guardar"}
              </Button>
            </div>
          )}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function DocumentBody({ doc }: { doc: { kind: string; template: string; language: string; created_at: string } }) {
  return (
    <dl className="divide-y divide-hairline/60">
      <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
        <dt className="text-xs font-medium text-stone">Tipo</dt>
        <dd className="text-sm text-ink">{doc.kind === "cover_letter" ? "Carta" : "CV"}</dd>
      </div>
      <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
        <dt className="text-xs font-medium text-stone">Plantilla</dt>
        <dd className="text-sm text-ink">{doc.template}</dd>
      </div>
      <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
        <dt className="text-xs font-medium text-stone">Idioma</dt>
        <dd className="text-sm text-ink uppercase">{doc.language}</dd>
      </div>
      <div className="grid grid-cols-[96px_1fr] gap-3 py-1.5">
        <dt className="text-xs font-medium text-stone">Creado</dt>
        <dd className="text-sm text-ink">{fmtDate(doc.created_at)}</dd>
      </div>
    </dl>
  );
}
