/**
 * NodeDetailDrawer — the rich panel that opens when a graph node is selected.
 *
 * Lazy-loads the entity's full content (per-kind list endpoint), its graph
 * neighbours, and any documents it sourced. Neighbours are clickable and
 * navigate the graph (parent re-selects → camera animates). The detail content
 * is rendered from a per-kind field spec so each kind shows what matters.
 */
import { useEffect, useMemo } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUpRight, MessageSquare, X } from "lucide-react";
import { Badge, Button } from "@/ui";
import { KIND_COLORS, KIND_LABELS, DEFAULT_KIND_COLOR } from "@/shared/kindColors";
import { iconFor } from "./nodeIcons";
import {
  kindHasDetail,
  useEntityDetail,
  type EntityRow,
} from "./entityDetail";
import type { GraphSnapshot } from "./api";
import type { GraphSelection } from "./GraphView";

type FieldType = "text" | "date" | "range" | "chips" | "bullets" | "link";
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
    { key: "years", label: "Años" },
    { key: "last_used_year", label: "Último uso" },
  ],
  education: [
    { key: "institution", label: "Institución" },
    { key: "field_of_study", label: "Área" },
    { key: "__range", label: "Periodo", type: "range" },
    { key: "gpa", label: "Nota" },
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

function fmtDate(v: unknown): string {
  if (!v) return "";
  const d = new Date(String(v));
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleDateString("es-ES", { month: "short", year: "numeric" });
}

function asArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x)).filter(Boolean);
  return [];
}

function Field({ spec, row }: { spec: FieldSpec; row: EntityRow }) {
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

  const color = kind ? KIND_COLORS[kind] ?? DEFAULT_KIND_COLOR : DEFAULT_KIND_COLOR;
  const row = data?.row ?? null;
  const doc = data?.document ?? null;
  const specs = kind ? FIELD_SPECS[kind] ?? [] : [];
  const title =
    (row && kind && (row[TITLE_KEY[kind] ?? "name"] as string)) || selection?.label || "";
  const confidence = typeof row?.confidence === "number" ? Math.round(row.confidence * 100) : null;

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

  // Esc closes the inspector without blocking the graph (no backdrop).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          key="inspector"
          initial={{ x: 24, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 24, opacity: 0 }}
          transition={{ type: "spring", stiffness: 420, damping: 40 }}
          className="node-inspector pointer-events-auto absolute right-4 top-4 z-30 flex max-h-[calc(100%-2rem)] w-[min(94%,360px)] flex-col overflow-hidden rounded-card border border-hairline shadow-float"
        >
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-start gap-3 bg-canvas/70 backdrop-blur px-5 pt-5 pb-4 border-b border-hairline">
              <span
                className="grid h-9 w-9 shrink-0 place-items-center rounded-full"
                style={{ backgroundColor: color }}
              >
                <img src={iconFor(kind ?? "")} alt="" className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="eyebrow">{kind ? KIND_LABELS[kind] ?? kind : ""}</p>
                <h3 className="font-display text-[19px] leading-tight text-ink break-words">
                  {title}
                </h3>
              </div>
              <button
                type="button"
                aria-label="Cerrar"
                onClick={onClose}
                className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-stone hover:text-ink hover:bg-surface transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <div className="px-5 py-4 space-y-5">
              {/* Meta chips */}
              {(confidence !== null || Boolean(row?.source) || Boolean(row?.is_current)) && (
                <div className="flex flex-wrap gap-1.5">
                  {row?.is_current ? <Badge tone="leaf" size="sm">Actual</Badge> : null}
                  {confidence !== null ? (
                    <Badge tone="stone" size="sm">{confidence}% confianza</Badge>
                  ) : null}
                  {row?.source ? (
                    <Badge tone="stone" size="sm">{String(row.source)}</Badge>
                  ) : null}
                </div>
              )}

              {/* Body */}
              {isLoading ? (
                <p className="text-sm text-stone">Cargando…</p>
              ) : doc ? (
                <DocumentBody doc={doc} />
              ) : row ? (
                <dl className="divide-y divide-hairline/60">
                  {specs.map((spec) => (
                    <Field key={spec.key} spec={spec} row={row} />
                  ))}
                </dl>
              ) : !kindHasDetail(kind ?? "") ? (
                <p className="text-sm text-stone leading-relaxed">
                  Este nodo no tiene una ficha detallada todavía. Pregúntale al agente
                  para profundizar.
                </p>
              ) : null}

              {/* Neighbours — derived from the graph's own edges */}
              {neighborList.length > 0 && (
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
            </div>
          </div>
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
