import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { FileDown, Sparkles, ChevronDown, Wand2 } from "lucide-react";
import { documents } from "@/shared/api";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  PageHeader,
  ProgressSteps,
  Reveal,
  Surface,
  Textarea,
  cn,
  type ProgressStep,
} from "@/ui";

export function GenerateCvPage() {
  const { t } = useTranslation();
  const [jobDesc, setJobDesc] = useState(_DEMO_JD);
  const [jobUrl, setJobUrl] = useState("");
  const [template, setTemplate] = useState("ats-classic");
  const [language, setLanguage] = useState<"es" | "en">("es");
  const [tone, setTone] = useState("professional");
  const [kind, setKind] = useState<"cv" | "cover_letter">("cv");
  const [showJson, setShowJson] = useState(false);

  // Prefill from JobsPage / chat-driven cover-letter proposal +
  // chat-driven `propose_cv_regenerate` (template / language / tone overrides).
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("cvs-saas-prefill-job");
      if (raw) {
        sessionStorage.removeItem("cvs-saas-prefill-job");
        const data = JSON.parse(raw) as {
          job_url?: string;
          job_description?: string;
        };
        if (data.job_url) setJobUrl(data.job_url);
        if (data.job_description) setJobDesc(data.job_description);
      }
      const kindHint = sessionStorage.getItem("cvs-saas-prefill-kind");
      if (kindHint === "cv" || kindHint === "cover_letter") {
        sessionStorage.removeItem("cvs-saas-prefill-kind");
        setKind(kindHint);
      }
      // `propose_cv_regenerate` drops template/language/tone overrides here.
      const regenRaw = sessionStorage.getItem("cvs-saas-cv-regenerate");
      if (regenRaw) {
        sessionStorage.removeItem("cvs-saas-cv-regenerate");
        const regen = JSON.parse(regenRaw) as {
          template?: string;
          language?: string;
          tone?: string;
        };
        if (regen.template) setTemplate(regen.template);
        if (regen.language === "es" || regen.language === "en") {
          setLanguage(regen.language);
        }
        if (regen.tone) setTone(regen.tone);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const gen = useMutation({
    mutationFn: () =>
      documents.generate({
        job_description: jobDesc || undefined,
        job_url: jobUrl || undefined,
        template,
        language,
        tone,
        kind,
      }),
  });

  return (
    <Surface width="xl" spacing="md">
      <PageHeader
        eyebrow="Generación"
        title={kind === "cover_letter" ? "Carta de presentación" : t("cv.generate")}
        subtitle="Pega una oferta o su URL. El agente adapta tu universo, no inventa nada que no tengas."
      />

      <Reveal>
        <div
          role="tablist"
          aria-label="Tipo de documento"
          className="inline-flex items-center gap-0.5 rounded-tag bg-surface p-1 text-xs font-medium self-start"
        >
          <KindTab active={kind === "cv"} onClick={() => setKind("cv")}>
            CV adaptado
          </KindTab>
          <KindTab active={kind === "cover_letter"} onClick={() => setKind("cover_letter")}>
            Carta de presentación
          </KindTab>
        </div>
      </Reveal>

      <div className="grid lg:grid-cols-[1.05fr_1fr] gap-6 md:gap-10">
        <Reveal>
          <Card padding="lg">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                gen.mutate();
              }}
              className="flex flex-col gap-5"
            >
              <Field label={t("cv.jobUrl")} hint="O pega la descripción abajo">
                {(p) => (
                  <Input
                    {...p}
                    value={jobUrl}
                    onChange={(e) => setJobUrl(e.target.value)}
                    placeholder="https://..."
                  />
                )}
              </Field>
              <Field label={t("cv.jobDescription")}>
                {(p) => (
                  <Textarea
                    {...p}
                    rows={10}
                    value={jobDesc}
                    onChange={(e) => setJobDesc(e.target.value)}
                  />
                )}
              </Field>

              {kind === "cv" && (
                <TemplateGallery value={template} onChange={setTemplate} />
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Field label="Plantilla">
                  {(p) => (
                    <Select
                      {...p}
                      value={template}
                      onChange={(e) => setTemplate(e.target.value)}
                    >
                      <option value="ats-classic">ATS clásica</option>
                      <option value="modern">Moderna (2 columnas)</option>
                      <option value="minimal">Minimal (serif)</option>
                    </Select>
                  )}
                </Field>
                <Field label="Idioma">
                  {(p) => (
                    <Select
                      {...p}
                      value={language}
                      onChange={(e) => setLanguage(e.target.value as "es" | "en")}
                    >
                      <option value="es">{t("cv.languageEs")}</option>
                      <option value="en">{t("cv.languageEn")}</option>
                    </Select>
                  )}
                </Field>
                <Field label="Tono">
                  {(p) => (
                    <Select
                      {...p}
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                    >
                      <option value="professional">{t("cv.toneProfessional")}</option>
                      <option value="conversational">{t("cv.toneConversational")}</option>
                    </Select>
                  )}
                </Field>
              </div>

              <Button
                type="submit"
                size="lg"
                fullWidth
                loading={gen.isPending}
                leadingIcon={<Wand2 size={16} />}
              >
                {gen.isPending
                  ? "Generando"
                  : kind === "cover_letter"
                    ? "Generar carta"
                    : t("cv.generate")}
              </Button>
              {gen.isError && (
                <p className="text-sm text-red-600">{(gen.error as Error).message}</p>
              )}
            </form>
          </Card>
        </Reveal>

        <Reveal delay={0.08}>
          <Card
            padding="lg"
            tone="canvas"
            bordered
            className="lg:sticky lg:top-24 flex flex-col gap-4"
          >
            <div className="flex items-center gap-2 text-sm font-medium text-ink">
              <Sparkles size={16} className="text-leaf-ink" />
              Resultado
            </div>

            <AnimatePresence mode="wait">
              {gen.isPending ? (
                <ProgressPanel key="progress" />
              ) : gen.data ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}
                  className="space-y-4"
                >
                  <div className="space-y-2">
                    <Badge tone="leaf" dot>
                      Documento listo
                    </Badge>
                    <div className="text-xs text-stone font-mono break-all">
                      {gen.data.document_id}
                    </div>
                  </div>
                  {kind === "cover_letter" &&
                    (gen.data.json_resume as any)?.cover_letter_body && (
                      <CoverLetterPreview
                        body={(gen.data.json_resume as any).cover_letter_body as string}
                      />
                    )}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {gen.data.pdf_url && (
                      <DownloadLink
                        href={gen.data.pdf_url}
                        label={t("cv.downloadPdf")}
                        ext="PDF"
                      />
                    )}
                    {gen.data.docx_url && (
                      <DownloadLink
                        href={gen.data.docx_url}
                        label={t("cv.downloadDocx")}
                        ext="DOCX"
                      />
                    )}
                    <DownloadLink
                      href={`/api/v1/documents/${gen.data.document_id}/json`}
                      label={t("cv.downloadJson")}
                      ext="JSON"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowJson((v) => !v)}
                    aria-expanded={showJson}
                    className="flex items-center justify-between w-full text-xs text-stone hover:text-ink transition-colors pt-2 border-t border-ink/5"
                  >
                    <span>JSON Resume</span>
                    <ChevronDown
                      size={14}
                      className={cn("transition-transform duration-180", showJson && "rotate-180")}
                    />
                  </button>
                  <AnimatePresence initial={false}>
                    {showJson && (
                      <motion.pre
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}
                        className="text-xs max-h-96 overflow-auto bg-surface p-3 rounded-card"
                      >
                        {JSON.stringify(gen.data.json_resume, null, 2)}
                      </motion.pre>
                    )}
                  </AnimatePresence>
                </motion.div>
              ) : (
                <EmptyState key="empty" />
              )}
            </AnimatePresence>
          </Card>
        </Reveal>
      </div>
    </Surface>
  );
}

const TEMPLATES = [
  {
    id: "ats-classic",
    label: "ATS clásica",
    description: "Una columna, headers fuertes. Pasa filtros ATS sin pelea.",
    Preview: AtsClassicPreview,
  },
  {
    id: "modern",
    label: "Moderna",
    description: "Dos columnas, sidebar con skills + idiomas, pills.",
    Preview: ModernPreview,
  },
  {
    id: "minimal",
    label: "Minimal",
    description: "Serif elegante, centrado, mucho whitespace.",
    Preview: MinimalPreview,
  },
];

function TemplateGallery({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {TEMPLATES.map((t) => {
        const active = value === t.id;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            aria-pressed={active}
            className={cn(
              "group flex flex-col gap-2 rounded-card p-2 text-left border transition-all duration-180 ease-pirsch",
              active
                ? "border-ink bg-canvas shadow-soft"
                : "border-ink/8 bg-canvas hover:border-ink/30",
            )}
          >
            <div className="aspect-[3/4] rounded-md bg-surface overflow-hidden">
              <t.Preview />
            </div>
            <div className="px-1">
              <div className="text-xs font-medium text-ink">{t.label}</div>
              <div className="text-[10px] text-stone leading-tight mt-0.5 line-clamp-2">
                {t.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function AtsClassicPreview() {
  return (
    <svg viewBox="0 0 90 120" className="w-full h-full" aria-hidden>
      <rect width="90" height="120" fill="#fff" />
      <rect x="10" y="12" width="40" height="6" fill="#0a0a0a" />
      <rect x="10" y="22" width="22" height="3" fill="#707070" />
      <line x1="10" y1="34" x2="80" y2="34" stroke="#999" strokeWidth="0.4" />
      <rect x="10" y="40" width="14" height="3" fill="#0a0a0a" />
      <rect x="10" y="47" width="60" height="2" fill="#aaa" />
      <rect x="10" y="52" width="55" height="2" fill="#aaa" />
      <rect x="10" y="57" width="50" height="2" fill="#aaa" />
      <line x1="10" y1="68" x2="80" y2="68" stroke="#999" strokeWidth="0.4" />
      <rect x="10" y="74" width="14" height="3" fill="#0a0a0a" />
      <rect x="10" y="81" width="60" height="2" fill="#aaa" />
      <rect x="10" y="86" width="40" height="2" fill="#aaa" />
      <line x1="10" y1="98" x2="80" y2="98" stroke="#999" strokeWidth="0.4" />
      <rect x="10" y="104" width="14" height="3" fill="#0a0a0a" />
      <rect x="10" y="110" width="65" height="2" fill="#aaa" />
    </svg>
  );
}

function ModernPreview() {
  return (
    <svg viewBox="0 0 90 120" className="w-full h-full" aria-hidden>
      <rect width="90" height="120" fill="#fff" />
      <rect x="10" y="10" width="50" height="6" fill="#0a0a0a" />
      <rect x="10" y="20" width="30" height="3" fill="#707070" />
      <rect x="10" y="28" width="70" height="2" fill="#aaa" />
      <line x1="34" y1="36" x2="34" y2="115" stroke="#ddd" strokeWidth="0.5" />
      <rect x="10" y="42" width="16" height="3" fill="#707070" />
      <rect x="10" y="48" width="6" height="3" rx="1.5" fill="#f8f5ed" stroke="#0a0a0a" strokeWidth="0.3" />
      <rect x="18" y="48" width="9" height="3" rx="1.5" fill="#f8f5ed" stroke="#0a0a0a" strokeWidth="0.3" />
      <rect x="10" y="54" width="8" height="3" rx="1.5" fill="#f8f5ed" stroke="#0a0a0a" strokeWidth="0.3" />
      <rect x="10" y="64" width="14" height="3" fill="#707070" />
      <rect x="10" y="71" width="20" height="2" fill="#aaa" />
      <rect x="10" y="76" width="22" height="2" fill="#aaa" />
      <rect x="40" y="42" width="14" height="3" fill="#707070" />
      <rect x="40" y="49" width="38" height="2" fill="#0a0a0a" />
      <rect x="40" y="54" width="40" height="2" fill="#aaa" />
      <rect x="40" y="59" width="34" height="2" fill="#aaa" />
      <rect x="40" y="66" width="36" height="2" fill="#aaa" />
      <rect x="40" y="76" width="38" height="2" fill="#0a0a0a" />
      <rect x="40" y="81" width="40" height="2" fill="#aaa" />
      <rect x="40" y="86" width="30" height="2" fill="#aaa" />
    </svg>
  );
}

function MinimalPreview() {
  return (
    <svg viewBox="0 0 90 120" className="w-full h-full" aria-hidden>
      <rect width="90" height="120" fill="#fff" />
      <rect x="25" y="22" width="40" height="6" fill="#0a0a0a" />
      <rect x="32" y="32" width="26" height="3" fill="#707070" />
      <line x1="20" y1="48" x2="70" y2="48" stroke="#ccc" strokeWidth="0.3" />
      <rect x="35" y="52" width="20" height="2" fill="#707070" />
      <rect x="20" y="62" width="50" height="2" fill="#aaa" />
      <rect x="20" y="67" width="48" height="2" fill="#aaa" />
      <rect x="20" y="72" width="52" height="2" fill="#aaa" />
      <rect x="20" y="84" width="18" height="2" fill="#707070" />
      <line x1="20" y1="88" x2="70" y2="88" stroke="#ccc" strokeWidth="0.3" />
      <rect x="20" y="94" width="50" height="2" fill="#aaa" />
      <rect x="20" y="99" width="46" height="2" fill="#aaa" />
      <rect x="20" y="108" width="14" height="2" fill="#707070" />
    </svg>
  );
}

function CoverLetterPreview({ body }: { body: string }) {
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(body);
    } catch {
      /* ignore */
    }
  };
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-stone font-medium">
          Vista previa
        </span>
        <button
          type="button"
          onClick={onCopy}
          className="text-xs text-stone hover:text-ink transition-colors"
        >
          Copiar
        </button>
      </div>
      <pre className="whitespace-pre-wrap text-sm leading-relaxed text-ink bg-surface p-4 rounded-card max-h-64 overflow-auto font-sans">
        {body}
      </pre>
    </div>
  );
}

function KindTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "rounded-tag px-4 py-1.5 transition-all duration-180 ease-pirsch",
        active ? "bg-canvas text-ink shadow-soft" : "text-stone hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center gap-3 py-10 text-center"
    >
      <span
        aria-hidden
        className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sunbeam-soft text-sunbeam-ink"
      >
        <FileDown size={20} />
      </span>
      <p className="text-sm text-stone">Genera para ver tu CV adaptado a la oferta.</p>
    </motion.div>
  );
}

function ProgressPanel() {
  const steps: ProgressStep[] = [
    { id: "read", label: "Leyendo la oferta", status: "done" },
    { id: "cross", label: "Cruzando con tu universo", status: "active" },
    { id: "write", label: "Escribiendo secciones", status: "pending" },
    { id: "render", label: "Renderizando PDF", status: "pending" },
  ];
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="py-2"
    >
      <ProgressSteps steps={steps} />
    </motion.div>
  );
}

function DownloadLink({
  href,
  label,
  ext,
}: {
  href: string;
  label: string;
  ext: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="group flex flex-col items-start gap-1 rounded-btn bg-surface px-3 py-2.5 transition-all duration-180 ease-pirsch hover:bg-surface/70 hover:-translate-y-[1px]"
    >
      <div className="flex items-center gap-1.5 text-stone group-hover:text-ink transition-colors">
        <FileDown size={12} />
        <span className="text-[10px] uppercase tracking-wider font-medium">{ext}</span>
      </div>
      <span className="text-xs text-ink truncate w-full">{label}</span>
    </a>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}
function Select({ className, children, ...rest }: SelectProps) {
  return (
    <div className="relative">
      <select
        {...rest}
        className={cn(
          "appearance-none block w-full rounded-input bg-black/[0.04] text-ink",
          "px-4 py-3 text-sm font-normal transition-colors duration-180 ease-pirsch",
          "border border-transparent focus:outline-none focus:border-ink focus:bg-black/[0.06]",
          "pr-9 cursor-pointer",
          className,
        )}
      >
        {children}
      </select>
      <ChevronDown
        size={16}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-stone pointer-events-none"
      />
    </div>
  );
}

const _DEMO_JD = `Senior Python Backend Engineer @ Acme Corp (Madrid)

Buscamos un/a Senior Backend Engineer con experiencia en FastAPI, PostgreSQL y Docker para liderar la migración a microservicios.

Imprescindible:
- 5+ años de experiencia con Python
- FastAPI o Django REST
- PostgreSQL avanzado
- Docker, Kubernetes

Valorable: AWS, MCP, observabilidad (OpenTelemetry), comunicación clara.`;
