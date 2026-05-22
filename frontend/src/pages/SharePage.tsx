import { useQuery } from "@tanstack/react-query";
import { FileDown, ExternalLink, Sparkles } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  PageSkeleton,
  PaperPlaneIllustration,
  Reveal,
  Surface,
} from "@/ui";

interface SharePayload {
  document_id: string;
  kind: string;
  template: string;
  language: string;
  created_at: string | null;
  json_resume: Record<string, unknown> | null;
  pdf_url: string | null;
}

async function fetchShare(token: string): Promise<SharePayload> {
  const resp = await fetch(`/api/v1/share/${encodeURIComponent(token)}`);
  if (!resp.ok) {
    if (resp.status === 410) throw new Error("expired");
    if (resp.status === 404) throw new Error("not_found");
    throw new Error(`HTTP ${resp.status}`);
  }
  return resp.json();
}

export function SharePage({ token }: { token: string }) {
  const query = useQuery({
    queryKey: ["share", token],
    queryFn: () => fetchShare(token),
    retry: false,
  });

  if (query.isLoading) return <PageSkeleton />;

  if (query.error) {
    const isExpired = (query.error as Error).message === "expired";
    return (
      <Surface width="sm" spacing="md">
        <Reveal>
          <Card padding="lg" className="text-center space-y-4">
            <PaperPlaneIllustration className="mx-auto" />
            <h1 className="text-heading-sm font-medium tracking-tight">
              {isExpired ? "Este enlace ha caducado" : "Enlace no válido"}
            </h1>
            <p className="text-sm text-stone">
              {isExpired
                ? "El propietario puede generarte uno nuevo desde su panel de documentos."
                : "Comprueba que la URL es correcta o pide al propietario que comparta de nuevo."}
            </p>
            <div className="pt-2">
              <Button onClick={() => (window.location.hash = "#/")}>
                Ir a Universo Profesional
              </Button>
            </div>
          </Card>
        </Reveal>
      </Surface>
    );
  }

  const data = query.data!;
  const resume = data.json_resume as Record<string, any> | null;
  const basic = (resume?.basics ?? {}) as Record<string, any>;
  const work = (resume?.work ?? []) as any[];
  const education = (resume?.education ?? []) as any[];
  const skills = (resume?.skills ?? []) as any[];

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1.5">
            <Sparkles size={12} className="text-leaf-ink" />
            Compartido contigo
          </span>
        }
        title={basic.name ?? "Currículum compartido"}
        subtitle={basic.label ?? data.kind.toUpperCase()}
        actions={
          data.pdf_url && (
            <Button
              onClick={() => window.open(data.pdf_url!, "_blank", "noopener,noreferrer")}
              leadingIcon={<FileDown size={14} />}
            >
              Descargar PDF
            </Button>
          )
        }
      />

      <Reveal>
        <Card padding="lg" className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Badge tone="leaf" size="sm">
              {data.kind}
            </Badge>
            <Badge tone="stone" size="sm">
              {data.template}
            </Badge>
            <Badge tone="stone" size="sm">
              {data.language?.toUpperCase()}
            </Badge>
            {data.created_at && (
              <Badge tone="stone" size="sm">
                {new Date(data.created_at).toLocaleDateString()}
              </Badge>
            )}
          </div>
          {basic.summary && (
            <p className="text-sm text-stone leading-relaxed pt-2 border-t border-ink/5 mt-3">
              {basic.summary}
            </p>
          )}
        </Card>
      </Reveal>

      {work.length > 0 && (
        <Reveal delay={0.05}>
          <Card padding="lg">
            <h2 className="text-heading-sm font-medium tracking-tight mb-4">
              Experiencia
            </h2>
            <ul className="space-y-4">
              {work.map((w, i) => (
                <li
                  key={i}
                  className="border-b border-ink/5 last:border-0 last:pb-0 pb-4"
                >
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
                </li>
              ))}
            </ul>
          </Card>
        </Reveal>
      )}

      {education.length > 0 && (
        <Reveal delay={0.1}>
          <Card padding="lg">
            <h2 className="text-heading-sm font-medium tracking-tight mb-4">
              Educación
            </h2>
            <ul className="space-y-3">
              {education.map((e, i) => (
                <li key={i} className="flex items-baseline justify-between gap-2 flex-wrap">
                  <div>
                    <div className="font-medium text-ink">
                      {e.studyType ?? e.degree} {e.area ? `· ${e.area}` : ""}
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
        <Reveal delay={0.15}>
          <Card padding="lg">
            <h2 className="text-heading-sm font-medium tracking-tight mb-4">
              Skills
            </h2>
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

      <Reveal delay={0.2}>
        <div className="text-center pt-6 pb-12">
          <p className="text-xs text-stone mb-3">
            ¿Quieres tu propio universo profesional vivo?
          </p>
          <Button
            variant="outline"
            onClick={() => (window.location.hash = "#/register")}
            trailingIcon={<ExternalLink size={12} />}
          >
            Crear cuenta gratis
          </Button>
        </div>
      </Reveal>
    </Surface>
  );
}
