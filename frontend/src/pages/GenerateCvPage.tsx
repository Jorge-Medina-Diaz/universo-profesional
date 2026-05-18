import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { documents } from "@/shared/api";

export function GenerateCvPage() {
  const { t } = useTranslation();
  const [jobDesc, setJobDesc] = useState(_DEMO_JD);
  const [jobUrl, setJobUrl] = useState("");
  const [template, setTemplate] = useState("ats-classic");
  const [language, setLanguage] = useState<"es" | "en">("es");
  const [tone, setTone] = useState("professional");

  const gen = useMutation({
    mutationFn: () =>
      documents.generate({
        job_description: jobDesc || undefined,
        job_url: jobUrl || undefined,
        template,
        language,
        tone,
      }),
  });

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">{t("cv.generate")}</h1>
      <div className="grid md:grid-cols-2 gap-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            gen.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <label className="label" htmlFor="job_url">{t("cv.jobUrl")}</label>
            <input id="job_url" className="input" value={jobUrl} onChange={(e) => setJobUrl(e.target.value)} placeholder="https://…" />
          </div>
          <div>
            <label className="label" htmlFor="job_desc">{t("cv.jobDescription")}</label>
            <textarea id="job_desc" rows={10} className="input" value={jobDesc} onChange={(e) => setJobDesc(e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label" htmlFor="tpl">Plantilla</label>
              <select id="tpl" className="input" value={template} onChange={(e) => setTemplate(e.target.value)}>
                <option value="ats-classic">{t("cv.templateAtsClassic")}</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="lang">Idioma</label>
              <select id="lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value as "es" | "en")}>
                <option value="es">{t("cv.languageEs")}</option>
                <option value="en">{t("cv.languageEn")}</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="tone">Tono</label>
              <select id="tone" className="input" value={tone} onChange={(e) => setTone(e.target.value)}>
                <option value="professional">{t("cv.toneProfessional")}</option>
                <option value="conversational">{t("cv.toneConversational")}</option>
              </select>
            </div>
          </div>
          <button className="btn-primary w-full" disabled={gen.isPending}>
            {gen.isPending ? "Generando…" : t("cv.generate")}
          </button>
          {gen.isError && <p className="text-sm text-red-600">{(gen.error as Error).message}</p>}
        </form>

        <aside>
          <h2 className="font-semibold mb-3">Resultado</h2>
          {gen.data ? (
            <div className="card space-y-3">
              <p className="text-sm">Documento <code>{gen.data.document_id}</code></p>
              <div className="flex gap-2">
                {gen.data.pdf_url && (
                  <a className="btn-secondary" href={gen.data.pdf_url} target="_blank" rel="noreferrer">{t("cv.downloadPdf")}</a>
                )}
                {gen.data.docx_url && (
                  <a className="btn-secondary" href={gen.data.docx_url} target="_blank" rel="noreferrer">{t("cv.downloadDocx")}</a>
                )}
                <a className="btn-secondary" href={`/api/v1/documents/${gen.data.document_id}/json`} target="_blank" rel="noreferrer">{t("cv.downloadJson")}</a>
              </div>
              <details className="text-xs">
                <summary className="cursor-pointer">JSON Resume</summary>
                <pre className="max-h-96 overflow-auto bg-gray-50 p-2 rounded mt-2">{JSON.stringify(gen.data.json_resume, null, 2)}</pre>
              </details>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Genera para ver tu CV adaptado.</p>
          )}
        </aside>
      </div>
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
