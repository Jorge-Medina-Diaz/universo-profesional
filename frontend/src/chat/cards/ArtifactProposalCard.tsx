/**
 * ArtifactProposalCard — HITL card to confirm a portfolio artifact.
 *
 * Shows agent's proposed type + title + url + (optional) year/description/
 * venue, lets the user adjust before persisting. Returns the payload to the
 * agent via `respond` (the agent's next step calls `upsert_artifact`).
 */
import { useMemo, useState } from "react";
import { ExternalLink, Globe } from "lucide-react";
import { Badge, Button, ChatMessageMotion, Input, Textarea, cn } from "@/ui";

export type ArtifactType =
  | "github_repo"
  | "talk"
  | "blog_post"
  | "oss_contrib"
  | "paper"
  | "podcast"
  | "video"
  | "book"
  | "other";

const TYPES: { id: ArtifactType; label: string; tone: string }[] = [
  { id: "github_repo", label: "Repo", tone: "bg-stone/15 text-ink" },
  { id: "talk", label: "Talk", tone: "bg-purple-100 text-purple-800" },
  { id: "blog_post", label: "Blog", tone: "bg-sky-100 text-sky-800" },
  { id: "oss_contrib", label: "OSS PR", tone: "bg-emerald-100 text-emerald-800" },
  { id: "paper", label: "Paper", tone: "bg-amber-100 text-amber-800" },
  { id: "podcast", label: "Podcast", tone: "bg-rose-100 text-rose-800" },
  { id: "video", label: "Vídeo", tone: "bg-fuchsia-100 text-fuchsia-800" },
  { id: "book", label: "Libro", tone: "bg-blue-100 text-blue-800" },
  { id: "other", label: "Otro", tone: "bg-stone/15 text-ink" },
];

export interface ArtifactProposalPayload {
  type: ArtifactType;
  title: string;
  url: string;
  year?: number;
  description?: string;
  venue?: string;
  linked_project_id?: string;
}

export interface ArtifactProposalCardProps {
  initialType: ArtifactType;
  initialTitle: string;
  initialUrl: string;
  initialYear?: number;
  initialDescription?: string;
  initialVenue?: string;
  initialLinkedProjectId?: string;
  pending: boolean;
  onConfirm: (payload: ArtifactProposalPayload) => void | Promise<void>;
  onCancel: () => void;
}

export function ArtifactProposalCard({
  initialType,
  initialTitle,
  initialUrl,
  initialYear,
  initialDescription,
  initialVenue,
  initialLinkedProjectId,
  pending,
  onConfirm,
  onCancel,
}: ArtifactProposalCardProps) {
  const [type, setType] = useState<ArtifactType>(initialType);
  const [title, setTitle] = useState(initialTitle);
  const [url, setUrl] = useState(initialUrl);
  const [year, setYear] = useState<string>(initialYear ? String(initialYear) : "");
  const [description, setDescription] = useState(initialDescription ?? "");
  const [venue, setVenue] = useState(initialVenue ?? "");

  const isUrlValid = useMemo(() => {
    if (!url.trim()) return false;
    try {
      const u = new URL(url.trim());
      return u.protocol === "http:" || u.protocol === "https:";
    } catch {
      return false;
    }
  }, [url]);

  const canSubmit = title.trim().length > 0 && isUrlValid;

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface my-3 max-w-lg shadow-soft border border-ink/[0.06] overflow-hidden">
        <header className="flex items-center gap-2 px-5 pt-5 pb-3">
          <span
            aria-hidden
            className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-sunbeam-soft text-sunbeam-ink"
          >
            <Globe size={14} />
          </span>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm text-ink">Añadir al portfolio</h4>
            <p className="text-xs text-stone">
              Repos, talks, blogs, papers o PRs públicos que reflejen tu trabajo.
            </p>
          </div>
        </header>

        <div className="px-5 pb-3 flex flex-col gap-3">
          {/* Type chips */}
          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              Tipo
            </label>
            <div className="flex flex-wrap gap-1.5">
              {TYPES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setType(t.id)}
                  aria-pressed={type === t.id}
                  className={cn(
                    "px-2.5 py-1 text-[11px] rounded-full transition-all border",
                    type === t.id
                      ? `${t.tone} border-transparent`
                      : "bg-surface text-stone border-hairline hover:border-ink/[0.2]",
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              Título
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej. 'RAG patterns in production'"
            />
          </div>

          {/* URL */}
          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              URL
            </label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/usuario/repo"
              aria-invalid={!isUrlValid && url.length > 0}
              className={
                url.length > 0 && !isUrlValid
                  ? "border-rose-300 focus-visible:ring-rose-200"
                  : undefined
              }
            />
            {url.length > 0 && !isUrlValid ? (
              <p className="text-[11px] text-rose-600 mt-1">URL no válida.</p>
            ) : null}
          </div>

          {/* Year + venue side by side */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
                Año
              </label>
              <Input
                type="number"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                placeholder="2025"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
                Venue (opcional)
              </label>
              <Input
                value={venue}
                onChange={(e) => setVenue(e.target.value)}
                placeholder="Ej. PyConES, Medium, ArXiv"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="text-[11px] uppercase tracking-wide text-stone font-medium mb-1 block">
              Descripción (opcional)
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Una línea sobre por qué importa esto en tu perfil."
            />
          </div>

          {initialLinkedProjectId ? (
            <div className="flex items-center gap-2 text-[11px] text-stone">
              <Badge tone="stone">Linked</Badge>
              <span className="truncate">
                vinculado al proyecto {initialLinkedProjectId.slice(0, 8)}…
              </span>
            </div>
          ) : null}
        </div>

        <footer className="border-t border-ink/[0.06] bg-canvas px-5 py-3 flex items-center justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            disabled={pending}
          >
            Descartar
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!canSubmit || pending}
            onClick={() => {
              const yearNum = year.trim() ? Number(year) : undefined;
              onConfirm({
                type,
                title: title.trim(),
                url: url.trim(),
                year: yearNum && !Number.isNaN(yearNum) ? yearNum : undefined,
                description: description.trim() || undefined,
                venue: venue.trim() || undefined,
                linked_project_id: initialLinkedProjectId,
              });
            }}
          >
            {pending ? "Guardando…" : "Guardar"}
            <ExternalLink size={12} className="ml-1" />
          </Button>
        </footer>
      </div>
    </ChatMessageMotion>
  );
}
