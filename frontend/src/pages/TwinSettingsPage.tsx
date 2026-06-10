import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, ExternalLink, RefreshCw, MessageCircle, Users, Inbox } from "lucide-react";

import { Button, Card, PageHeader, Stagger, Surface, toast } from "@/ui";
import { twin, type TwinCuration } from "@/shared/api";
import { queryKeys } from "@/shared/queryKeys";

const KIND_LABELS: Record<string, string> = {
  experience: "Experiencias",
  education: "Formación",
  skill: "Habilidades",
  project: "Proyectos",
  certification: "Certificaciones",
  language: "Idiomas",
  achievement: "Logros",
};

export function TwinSettingsPage() {
  const qc = useQueryClient();
  const config = useQuery({ queryKey: queryKeys.twin.config, queryFn: () => twin.get() });

  const update = useMutation({
    mutationFn: twin.update,
    onSuccess: (data) => {
      qc.setQueryData(queryKeys.twin.config, data);
      toast.success("Twin actualizado");
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : "No se pudo guardar el twin"),
  });
  const regen = useMutation({
    mutationFn: twin.regenerateSlug,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.twin.config });
      toast.success("Nueva URL generada — la anterior ha dejado de funcionar");
    },
    onError: () => toast.error("No se pudo regenerar la URL"),
  });

  // Local curation draft, seeded from the server config.
  const [draft, setDraft] = useState<TwinCuration | null>(null);
  useEffect(() => {
    if (config.data && draft === null) setDraft(config.data.curation);
  }, [config.data, draft]);

  if (config.isLoading) {
    return (
      <Surface width="lg" spacing="md">
        <p className="text-sm text-stone py-12 text-center">Cargando…</p>
      </Surface>
    );
  }
  if (config.isError || !config.data) {
    return (
      <Surface width="lg" spacing="md">
        <p className="text-sm text-danger py-12 text-center" role="alert">
          No se pudo cargar la configuración del twin.
        </p>
      </Surface>
    );
  }

  const cfg = config.data;
  const publicUrl = cfg.slug ? `${window.location.origin}/#/t/${cfg.slug}` : null;
  const embedSnippet = cfg.slug
    ? `<iframe src="${window.location.origin}/#/t/${cfg.slug}?embed=1" width="420" height="480" style="border:1px solid #e5e5e5;border-radius:16px" title="Gemelo digital"></iframe>`
    : null;

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Compartir"
        title="Mi gemelo digital"
        subtitle="Un agente público que responde sobre tu trayectoria — solo con lo que tú decidas compartir."
      />
      <Stagger className="flex flex-col gap-4 md:gap-6" delayStep={0.05}>
        <Card padding="lg">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="font-medium text-ink mb-1">Estado</h2>
              <p className="text-sm text-stone">
                {cfg.enabled
                  ? "Tu twin está publicado: cualquiera con el enlace puede chatear con él."
                  : "Desactivado: el enlace público no resuelve."}
              </p>
            </div>
            <Button
              variant={cfg.enabled ? "secondary" : "primary"}
              loading={update.isPending}
              onClick={() => update.mutate({ enabled: !cfg.enabled })}
            >
              {cfg.enabled ? "Desactivar" : "Publicar twin"}
            </Button>
          </div>
          {publicUrl && cfg.enabled && (
            <div className="mt-4 flex flex-col gap-3">
              <CopyRow label="URL pública" value={publicUrl}>
                <a
                  href={publicUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-stone hover:text-ink"
                  aria-label="Abrir en otra pestaña"
                >
                  <ExternalLink size={14} />
                </a>
              </CopyRow>
              {embedSnippet && (
                <CopyRow label="Widget para tu portfolio (iframe)" value={embedSnippet} mono />
              )}
              <div>
                <Button
                  variant="ghost"
                  size="sm"
                  loading={regen.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        "¿Generar una nueva URL? La actual dejará de funcionar al instante.",
                      )
                    )
                      regen.mutate();
                  }}
                >
                  <RefreshCw size={13} className="mr-1.5" /> Regenerar URL (revoca la actual)
                </Button>
              </div>
            </div>
          )}
        </Card>

        {draft && (
          <Card padding="lg">
            <h2 className="font-medium text-ink mb-1">Qué puede contar</h2>
            <p className="text-sm text-stone mb-4">
              Notas, metas, diario y preferencias NUNCA se exponen. Aquí eliges qué tipos
              profesionales ve el twin.
            </p>
            <div className="flex flex-wrap gap-2 mb-5">
              {cfg.allowed_kinds.map((k) => {
                const active = draft.visible_kinds.includes(k);
                return (
                  <button
                    key={k}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      setDraft({
                        ...draft,
                        visible_kinds: active
                          ? draft.visible_kinds.filter((x) => x !== k)
                          : [...draft.visible_kinds, k],
                      })
                    }
                    className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                      active
                        ? "bg-nova/15 border-nova/40 text-ink"
                        : "bg-surface border-hairline text-stone hover:text-ink"
                    }`}
                  >
                    {KIND_LABELS[k] ?? k}
                  </button>
                );
              })}
            </div>
            <label className="block text-sm text-ink mb-1.5" htmlFor="twin-charter">
              Pautas para el twin
            </label>
            <textarea
              id="twin-charter"
              value={draft.charter}
              onChange={(e) => setDraft({ ...draft, charter: e.target.value })}
              maxLength={500}
              rows={3}
              className="w-full px-3 py-2 rounded-lg bg-canvas border border-hairline text-sm text-ink outline-none focus:border-nova/50 resize-none"
            />
            <label className="block text-sm text-ink mt-4 mb-1.5" htmlFor="twin-questions">
              Preguntas sugeridas (una por línea, máx. 5)
            </label>
            <textarea
              id="twin-questions"
              value={draft.suggested_questions.join("\n")}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  suggested_questions: e.target.value.split("\n").slice(0, 5),
                })
              }
              rows={3}
              placeholder="¿Cuál fue tu mayor proyecto cloud?"
              className="w-full px-3 py-2 rounded-lg bg-canvas border border-hairline text-sm text-ink placeholder:text-stone outline-none focus:border-nova/50 resize-none"
            />
            <div className="mt-4">
              <Button
                loading={update.isPending}
                onClick={() =>
                  update.mutate({
                    curation: {
                      ...draft,
                      suggested_questions: draft.suggested_questions
                        .map((q) => q.trim())
                        .filter(Boolean),
                    },
                  })
                }
              >
                Guardar curación
              </Button>
            </div>
          </Card>
        )}

        <Card padding="lg">
          <h2 className="font-medium text-ink mb-4">Actividad</h2>
          <div className="grid grid-cols-3 gap-3 mb-5">
            <Stat icon={<Users size={15} />} label="Sesiones (7 días)" value={cfg.stats.sessions_7d} />
            <Stat
              icon={<MessageCircle size={15} />}
              label="Preguntas recientes"
              value={cfg.stats.recent_questions.length}
            />
            <Stat icon={<Inbox size={15} />} label="Contactos" value={cfg.stats.leads.length} />
          </div>
          {cfg.stats.recent_questions.length > 0 && (
            <>
              <h3 className="text-sm text-ink mb-2">Qué preguntan</h3>
              <ul className="flex flex-col gap-1.5 mb-5">
                {cfg.stats.recent_questions.map((q, i) => (
                  <li key={i} className="text-sm text-stone truncate">
                    “{q.question}”
                  </li>
                ))}
              </ul>
            </>
          )}
          {cfg.stats.leads.length > 0 && (
            <>
              <h3 className="text-sm text-ink mb-2">Contactos recibidos</h3>
              <ul className="flex flex-col gap-2">
                {cfg.stats.leads.map((l, i) => (
                  <li key={i} className="text-sm rounded-lg border border-hairline bg-surface/60 px-3 py-2">
                    <span className="text-ink">{l.contact}</span>
                    {l.message && <span className="text-stone"> — {l.message}</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {cfg.stats.sessions_7d === 0 && cfg.stats.leads.length === 0 && (
            <p className="text-sm text-stone">
              Aún no hay visitas. Comparte tu URL pública o incrusta el widget en tu portfolio.
            </p>
          )}
        </Card>
      </Stagger>
    </Surface>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-hairline bg-surface/60 px-3 py-3">
      <div className="flex items-center gap-1.5 text-stone mb-1">{icon}<span className="text-[11px]">{label}</span></div>
      <p className="text-xl text-ink font-display">{value}</p>
    </div>
  );
}

function CopyRow({
  label,
  value,
  mono,
  children,
}: {
  label: string;
  value: string;
  mono?: boolean;
  children?: React.ReactNode;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <div>
      <p className="text-xs text-stone mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <code
          className={`flex-1 truncate text-xs bg-surface border border-hairline rounded-lg px-2.5 py-2 text-ink ${mono ? "font-mono" : ""}`}
        >
          {value}
        </code>
        <button
          type="button"
          aria-label={`Copiar ${label}`}
          onClick={() => {
            void navigator.clipboard.writeText(value).then(() => {
              setCopied(true);
              setTimeout(() => setCopied(false), 1800);
            });
          }}
          className="h-8 w-8 grid place-items-center rounded-lg border border-hairline text-stone hover:text-ink transition-colors"
        >
          {copied ? <Check size={14} className="text-leaf" /> : <Copy size={14} />}
        </button>
        {children}
      </div>
    </div>
  );
}

export default TwinSettingsPage;
