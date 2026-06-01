/**
 * Interview preparation for a single job (R16): a research brief, a question
 * bank, and STAR answer drafts grounded in the user's universe. Generated
 * on-demand and persisted server-side (one prep per job).
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Sparkles } from "lucide-react";
import { jobs } from "@/shared/api";
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

export function InterviewPrepPage({ jobId }: { jobId: string }) {
  const qc = useQueryClient();
  const prepKey = ["interview-prep", jobId] as const;

  const prep = useQuery({
    queryKey: prepKey,
    queryFn: () => jobs.interviewPrep.get(jobId),
  });

  const gen = useMutation({
    mutationFn: () => jobs.interviewPrep.generate(jobId),
    onSuccess: (data) => {
      qc.setQueryData(prepKey, data);
      toast.success("Preparación lista");
    },
    onError: () =>
      toast.error("No se pudo generar la preparación. Inténtalo de nuevo."),
  });

  const artifacts = prep.data?.artifacts ?? null;

  return (
    <Surface width="md" spacing="md">
      <button
        type="button"
        onClick={() => {
          window.location.hash = "#/jobs";
        }}
        className="flex items-center gap-1.5 text-sm text-stone hover:text-ink transition-colors"
      >
        <ArrowLeft size={14} /> Volver a ofertas
      </button>

      <PageHeader
        eyebrow="Entrevista"
        title="Preparación de entrevista"
        subtitle="Brief de investigación, banco de preguntas y borradores STAR — anclados en tu universo y en esta oferta."
      />

      {prep.isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Button
              variant="cta"
              onClick={() => gen.mutate()}
              disabled={gen.isPending}
              leadingIcon={<Sparkles size={14} />}
            >
              {gen.isPending
                ? "Generando…"
                : artifacts
                  ? "Regenerar"
                  : "Generar preparación"}
            </Button>
            {prep.data?.generated_by && (
              <Badge tone="stone" size="sm">
                {prep.data.generated_by.startsWith("ai") ? "IA" : "Plantilla"}
              </Badge>
            )}
          </div>

          {!artifacts && !gen.isPending && (
            <p className="text-sm text-stone">
              Aún no hay preparación para esta oferta. Genérala a partir de tu
              universo y la descripción del puesto.
            </p>
          )}

          {artifacts && (
            <Reveal>
              <div className="space-y-4">
                <Card padding="lg" tone="glass" className="space-y-2">
                  <h2 className="text-sm font-medium text-ink">Brief de investigación</h2>
                  <p className="text-sm text-stone leading-relaxed whitespace-pre-line">
                    {artifacts.research_brief}
                  </p>
                </Card>

                {artifacts.questions.length > 0 && (
                  <Card padding="lg" tone="glass" className="space-y-2">
                    <h2 className="text-sm font-medium text-ink">
                      Preguntas probables
                    </h2>
                    <ol className="space-y-1.5 list-decimal list-inside">
                      {artifacts.questions.map((q, i) => (
                        <li key={i} className="text-sm text-stone leading-relaxed">
                          {q}
                        </li>
                      ))}
                    </ol>
                  </Card>
                )}

                {artifacts.star_drafts.length > 0 && (
                  <Card padding="lg" tone="glass" className="space-y-3">
                    <h2 className="text-sm font-medium text-ink">
                      Borradores STAR
                    </h2>
                    <p className="text-xs text-stone">
                      Situación · Tarea · Acción · Resultado. Completa los huecos
                      con tus datos reales antes de la entrevista.
                    </p>
                    <div className="space-y-3">
                      {artifacts.star_drafts.map((s, i) => (
                        <div
                          key={i}
                          className="rounded-card border border-ink/5 bg-surface p-3 space-y-1.5"
                        >
                          <p className="text-sm font-medium text-ink">{s.prompt}</p>
                          <StarLine label="Situación" value={s.situation} />
                          <StarLine label="Tarea" value={s.task} />
                          <StarLine label="Acción" value={s.action} />
                          <StarLine label="Resultado" value={s.result} />
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            </Reveal>
          )}
        </div>
      )}
    </Surface>
  );
}

function StarLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-xs text-stone">
      <span className="font-medium text-ink">{label}:</span>{" "}
      {value ? value : <span className="italic opacity-70">por completar</span>}
    </p>
  );
}
