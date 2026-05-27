/**
 * Inline viewer for a generated document (CV or cover letter).
 * Renders JSON Resume nicely on screen + lets you download PDF/DOCX/JSON
 * or share. Reuses the same look as the public SharePage but for owner.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { FileDown, Share2, ArrowLeft, Sparkles, FileText, Pencil } from "lucide-react";
import { documents } from "@/shared/api";
import { useChatState } from "@/chat/state";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  PageSkeleton,
  Reveal,
  Surface,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

const SECTION_PROMPTS: Record<string, string> = {
  experience:
    "Quiero mejorar la sección de experiencia de mi CV. ¿Qué bullets podemos reescribir para que reflejen mejor mi impacto?",
  education:
    "Repasemos la sección de educación de mi CV. ¿Quitamos algo? ¿Añadimos detalle relevante?",
  skills:
    "Revisemos las skills del CV. ¿Cuáles son redundantes? ¿Faltan alguna importante de mi universo?",
  projects:
    "Mejoremos la sección de proyectos del CV. ¿Cuáles aportan más para esta oferta?",
};

function EditSectionButton({ section, docId }: { section: string; docId: string }) {
  const onClick = () => {
    const prompt = SECTION_PROMPTS[section];
    if (!prompt) return;
    useChatState.getState().setPendingInjection({
      content: `${prompt}\n\n(Contexto: documento ${docId}, sección ${section})`,
    });
    window.location.hash = "#/";
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 text-xs text-stone hover:text-ink transition-colors px-2 py-1 rounded-btn hover:bg-black/[0.04]"
      title="Refinar esta sección con el agente"
    >
      <Pencil size={11} />
      <span>Refinar con agente</span>
    </button>
  );
}

export function DocumentViewerPage({ id }: { id: string }) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.documents.detail(id),
    queryFn: () => documents.get(id),
    retry: false,
  });
  const share = useMutation({
    mutationFn: () => documents.share(id),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: queryKeys.documents.all });
      qc.invalidateQueries({ queryKey: queryKeys.documents.detail(id) });
      const url = `${window.location.origin}/#/share/${res?.share_token ?? ""}`;
      void navigator.clipboard?.writeText(url).catch(() => {});
      toast.success("Enlace copiado", "Listo para compartir");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos generar el enlace", (e as Error).message),
  });

  useEffect(() => {
    if (!query.data && !query.isLoading && query.isError) {
      toast.error("Documento no encontrado");
    }
  }, [query.data, query.isLoading, query.isError]);

  if (query.isLoading) return <PageSkeleton />;
  if (!query.data) {
    return (
      <Surface width="md" spacing="md">
        <Card padding="lg" className="text-center space-y-3">
          <FileText size={32} className="mx-auto text-stone" />
          <h2 className="text-heading-sm font-medium tracking-tight">
            Documento no encontrado
          </h2>
          <Button
            variant="outline"
            onClick={() => (window.location.hash = "#/documents")}
            leadingIcon={<ArrowLeft size={14} />}
          >
            Volver a documentos
          </Button>
        </Card>
      </Surface>
    );
  }

  const doc = query.data;
  const isCoverLetter = doc.kind === "cover_letter";
  const resume = doc.content_json as Record<string, any> | null;
  const basic = (resume?.basics ?? {}) as Record<string, any>;
  const coverBody = (resume as any)?.cover_letter_body as string | undefined;
  const work = (resume?.work ?? []) as any[];
  const education = (resume?.education ?? []) as any[];
  const skills = (resume?.skills ?? []) as any[];
  const projects = (resume?.projects ?? []) as any[];
  const languages = (resume?.languages ?? []) as any[];

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow={isCoverLetter ? "Carta" : "CV"}
        title={basic.name ?? doc.kind.toUpperCase()}
        subtitle={basic.label ?? `${doc.template} · ${doc.language?.toUpperCase()}`}
        actions={
          <>
            <Button
              variant="ghost"
              onClick={() => (window.location.hash = "#/documents")}
              leadingIcon={<ArrowLeft size={14} />}
            >
              Volver
            </Button>
            <Button
              variant="outline"
              onClick={() => share.mutate()}
              loading={share.isPending}
              leadingIcon={<Share2 size={14} />}
            >
              Compartir
            </Button>
            {doc.has_pdf && (
              <Button
                onClick={() =>
                  window.open(`/api/v1/documents/${id}/pdf`, "_blank", "noopener,noreferrer")
                }
                leadingIcon={<FileDown size={14} />}
              >
                Descargar PDF
              </Button>
            )}
          </>
        }
      />

      <Reveal>
        <Card padding="lg" className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Badge tone="leaf" size="sm">
              {doc.kind}
            </Badge>
            <Badge tone="stone" size="sm">
              {doc.template}
            </Badge>
            <Badge tone="stone" size="sm">
              {doc.language?.toUpperCase()}
            </Badge>
            {doc.created_at && (
              <Badge tone="stone" size="sm">
                {new Date(doc.created_at).toLocaleString()}
              </Badge>
            )}
            {doc.share_token && (
              <Badge tone="sunbeam" size="sm" dot>
                Compartido
              </Badge>
            )}
          </div>
        </Card>
      </Reveal>

      {/* Cover letter body */}
      {isCoverLetter && coverBody && (
        <Reveal delay={0.05}>
          <Card padding="lg">
            <h2 className="text-heading-sm font-medium tracking-tight mb-3 inline-flex items-center gap-2">
              <Sparkles size={16} className="text-sunbeam-ink" />
              Cuerpo de la carta
            </h2>
            <pre className="whitespace-pre-wrap text-sm leading-relaxed text-ink font-sans">
              {coverBody}
            </pre>
          </Card>
        </Reveal>
      )}

      {/* CV sections — hidden for cover letter */}
      {!isCoverLetter && (
        <>
          {basic.summary && (
            <Reveal delay={0.05}>
              <Card padding="lg">
                <h2 className="text-heading-sm font-medium tracking-tight mb-3">
                  Resumen
                </h2>
                <p className="text-sm text-ink leading-relaxed">{basic.summary}</p>
              </Card>
            </Reveal>
          )}

          {work.length > 0 && (
            <Reveal delay={0.07}>
              <Card padding="lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-heading-sm font-medium tracking-tight">
                    Experiencia
                  </h2>
                  <EditSectionButton section="experience" docId={id} />
                </div>
                <ul className="space-y-4">
                  {work.map((w, i) => (
                    <li key={i} className="border-b border-ink/5 last:border-0 pb-4 last:pb-0">
                      <div className="flex items-baseline justify-between gap-2 flex-wrap">
                        <h3 className="font-medium text-ink">{w.position ?? w.role}</h3>
                        <span className="text-xs text-stone">
                          {w.startDate ?? ""}
                          {w.startDate || w.endDate ? " — " : ""}
                          {w.endDate ?? "Actual"}
                        </span>
                      </div>
                      <p className="text-sm text-stone">{w.name ?? w.company}</p>
                      {w.summary && (
                        <p className="text-sm text-ink mt-1.5 leading-relaxed">
                          {w.summary}
                        </p>
                      )}
                      {(w.highlights ?? []).length > 0 && (
                        <ul className="list-disc pl-5 mt-1.5 space-y-1 text-sm text-ink">
                          {w.highlights.map((h: string, j: number) => (
                            <li key={j}>{h}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          )}

          {education.length > 0 && (
            <Reveal delay={0.09}>
              <Card padding="lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-heading-sm font-medium tracking-tight">
                    Educación
                  </h2>
                  <EditSectionButton section="education" docId={id} />
                </div>
                <ul className="space-y-3">
                  {education.map((e, i) => (
                    <li key={i} className="flex items-baseline justify-between gap-2 flex-wrap">
                      <div>
                        <div className="font-medium text-ink">
                          {e.studyType ?? e.degree}
                          {e.area ? ` · ${e.area}` : ""}
                        </div>
                        <div className="text-sm text-stone">{e.institution}</div>
                      </div>
                      <span className="text-xs text-stone">
                        {e.startDate ?? ""}
                        {e.startDate || e.endDate ? " — " : ""}
                        {e.endDate ?? ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          )}

          {skills.length > 0 && (
            <Reveal delay={0.11}>
              <Card padding="lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-heading-sm font-medium tracking-tight">Skills</h2>
                  <EditSectionButton section="skills" docId={id} />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {skills.map((s, i) => (
                    <span
                      key={i}
                      className="text-xs rounded-tag bg-canvas text-ink px-3 py-1 border border-ink/8"
                    >
                      {s.name}
                    </span>
                  ))}
                </div>
              </Card>
            </Reveal>
          )}

          {projects.length > 0 && (
            <Reveal delay={0.13}>
              <Card padding="lg">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-heading-sm font-medium tracking-tight">
                    Proyectos
                  </h2>
                  <EditSectionButton section="projects" docId={id} />
                </div>
                <ul className="space-y-3">
                  {projects.map((p, i) => (
                    <li key={i}>
                      <div className="font-medium text-ink">{p.name}</div>
                      {p.description && (
                        <p className="text-sm text-stone leading-relaxed">{p.description}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          )}

          {languages.length > 0 && (
            <Reveal delay={0.15}>
              <Card padding="lg">
                <h2 className="text-heading-sm font-medium tracking-tight mb-3">
                  Idiomas
                </h2>
                <div className="flex flex-wrap gap-2">
                  {languages.map((l, i) => (
                    <Badge key={i} tone="stone">
                      {l.language} · {l.fluency}
                    </Badge>
                  ))}
                </div>
              </Card>
            </Reveal>
          )}
        </>
      )}
    </Surface>
  );
}
