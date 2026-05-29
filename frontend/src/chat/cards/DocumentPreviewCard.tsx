/**
 * Display-only preview of a generated document inside the chat.
 *
 * The agent passes a document id (or compact metadata) and we fetch the JSON
 * Resume content lazily. Collapsible sections render summary, top experience,
 * top skills, languages, certifications — plus CTAs to download PDF/DOCX,
 * save, generate variants, or open the full editor.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  Copy,
  FileDown,
  FileText,
  FolderOpen,
  RotateCw,
  Sparkles,
} from "lucide-react";
import { documents } from "@/shared/api";
import { Badge, Button, ChatMessageMotion, cn, toast } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";
import type { JsonResume } from "@/shared/hooks/useJsonResume";

export interface DocumentPreviewCardProps {
  documentId: string;
  /** Optional CTA — agent wires it to `propose_cv_regenerate` */
  onRegenerate?: () => void;
  /** Optional CTA — agent wires it to `propose_document_generation` for a variant */
  onGenerateVariant?: () => void;
}

export function DocumentPreviewCard({
  documentId,
  onRegenerate,
  onGenerateVariant,
}: DocumentPreviewCardProps) {
  const query = useQuery({
    queryKey: queryKeys.documents.detail(documentId),
    queryFn: () => documents.get(documentId),
  });
  const [openSection, setOpenSection] = useState<string | null>("summary");

  if (query.isLoading) {
    return (
      <ChatMessageMotion>
        <div className="rounded-card bg-surface p-4 my-3 max-w-md border border-ink/[0.06] animate-pulse">
          <div className="h-4 w-1/2 bg-canvas/60 rounded mb-2" />
          <div className="h-3 w-1/3 bg-canvas/60 rounded mb-4" />
          <div className="h-16 bg-canvas/60 rounded" />
        </div>
      </ChatMessageMotion>
    );
  }
  if (!query.data) return null;
  const doc = query.data;
  const resume = (doc.content_json ?? {}) as JsonResume;
  const basics = resume.basics ?? {};
  const coverBody = resume.cover_letter_body;
  const work = resume.work ?? [];
  const skills = resume.skills ?? [];
  const targetJobTitle = basics.label as string | undefined;

  return (
    <ChatMessageMotion>
      <div className="rounded-card bg-surface p-4 my-3 max-w-md border border-ink/[0.06] shadow-soft">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-2.5 min-w-0">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink shrink-0">
              <FileText size={14} />
            </span>
            <div className="min-w-0 space-y-1">
              <h4 className="text-sm font-medium text-ink leading-tight truncate">
                {basics.name ?? (doc.kind === "cover_letter" ? "Carta" : "CV")}
              </h4>
              {targetJobTitle && (
                <p className="text-[11px] text-stone truncate">{targetJobTitle}</p>
              )}
              <div className="flex items-center gap-1.5 flex-wrap">
                <Badge tone="stone" size="sm">
                  {doc.kind === "cover_letter" ? "Carta" : "CV"}
                </Badge>
                <Badge tone="stone" size="sm">
                  {doc.template}
                </Badge>
                {doc.tone && (
                  <Badge tone="leaf" size="sm">
                    {doc.tone}
                  </Badge>
                )}
                <Badge tone="stone" size="sm">
                  {doc.language.toUpperCase()}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {coverBody && (
          <Section
            title="Carta"
            open={openSection === "cover"}
            onToggle={() => setOpenSection((s) => (s === "cover" ? null : "cover"))}
          >
            <pre className="whitespace-pre-wrap text-xs leading-relaxed text-ink font-sans max-h-48 overflow-auto">
              {coverBody}
            </pre>
          </Section>
        )}

        {!coverBody && basics.summary && (
          <Section
            title="Resumen"
            open={openSection === "summary"}
            onToggle={() => setOpenSection((s) => (s === "summary" ? null : "summary"))}
          >
            <p className="text-xs text-ink leading-relaxed">{basics.summary}</p>
          </Section>
        )}

        {!coverBody && work.length > 0 && (
          <Section
            title={`Experiencia (${work.length})`}
            open={openSection === "work"}
            onToggle={() => setOpenSection((s) => (s === "work" ? null : "work"))}
          >
            <ul className="text-xs space-y-2">
              {work.slice(0, 3).map((w, i) => (
                <li key={i}>
                  <div className="font-medium text-ink leading-tight">
                    {w.position ?? w.role} — {w.name ?? w.company}
                  </div>
                  <div className="text-[11px] text-stone">
                    {w.startDate ?? ""} — {w.endDate ?? "Actual"}
                  </div>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {!coverBody && skills.length > 0 && (
          <Section
            title={`Skills (${skills.length})`}
            open={openSection === "skills"}
            onToggle={() => setOpenSection((s) => (s === "skills" ? null : "skills"))}
          >
            <div className="flex flex-wrap gap-1">
              {skills.slice(0, 14).map((s, i) => (
                <span
                  key={i}
                  className="text-[11px] rounded-tag bg-canvas text-ink px-2 py-0.5"
                >
                  {s.name}
                </span>
              ))}
              {skills.length > 14 && (
                <span className="text-[11px] text-stone py-0.5">
                  +{skills.length - 14}
                </span>
              )}
            </div>
          </Section>
        )}

        <div className="flex gap-2 mt-3 flex-wrap">
          {doc.has_pdf && (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                window.open(
                  `/api/v1/documents/${doc.id}/pdf`,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
              leadingIcon={<FileDown size={12} />}
            >
              PDF
            </Button>
          )}
          {doc.has_docx && (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                window.open(
                  `/api/v1/documents/${doc.id}/docx`,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
              leadingIcon={<FileDown size={12} />}
            >
              DOCX
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => (window.location.hash = `#/documents/${doc.id}`)}
            leadingIcon={<Sparkles size={12} />}
          >
            Ver completo
          </Button>
          {onGenerateVariant && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onGenerateVariant}
              leadingIcon={<Copy size={12} />}
            >
              Variante
            </Button>
          )}
          {onRegenerate && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onRegenerate}
              leadingIcon={<RotateCw size={12} />}
            >
              Regenerar
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={async () => {
              try {
                const res = await documents.share(doc.id);
                if (res.share_url) {
                  await navigator.clipboard?.writeText(res.share_url);
                  toast.success("Enlace para compartir copiado al portapapeles");
                } else {
                  toast.success("Documento compartido");
                }
              } catch (e) {
                toast.error(
                  "No se pudo crear el enlace para compartir",
                  e instanceof Error ? e.message : undefined,
                );
              }
            }}
            leadingIcon={<FolderOpen size={12} />}
          >
            Copiar enlace
          </Button>
        </div>
      </div>
    </ChatMessageMotion>
  );
}

function Section({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-ink/5 first:border-t-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-2 py-2.5 text-left text-xs uppercase tracking-wider text-stone font-medium hover:text-ink transition-colors"
      >
        <span>{title}</span>
        <ChevronDown
          size={12}
          className={cn("transition-transform duration-180", open && "rotate-180")}
        />
      </button>
      {open && <div className="pb-3 pt-1">{children}</div>}
    </div>
  );
}
