import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documents } from "@/shared/api";

export function DocumentsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["documents"], queryFn: () => documents.list() });
  const share = useMutation({
    mutationFn: (id: string) => documents.share(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Documentos</h1>
        <a href="#/cv/new" className="btn-primary">{t("cv.generate")}</a>
      </header>
      {list.isLoading && <p>{t("common.loading")}</p>}
      <ul className="space-y-3">
        {list.data?.map((d) => (
          <li key={d.id} className="card">
            <header className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">{d.kind.toUpperCase()} · {d.template} · {d.language}</h3>
                <p className="text-xs text-gray-500">{new Date(d.created_at).toLocaleString()}</p>
              </div>
              <div className="flex gap-2">
                {d.has_pdf && <a className="btn-secondary" href={`/api/v1/documents/${d.id}/pdf`} target="_blank" rel="noreferrer">PDF</a>}
                {d.has_docx && <a className="btn-secondary" href={`/api/v1/documents/${d.id}/docx`} target="_blank" rel="noreferrer">DOCX</a>}
                <a className="btn-secondary" href={`/api/v1/documents/${d.id}/json`} target="_blank" rel="noreferrer">JSON</a>
                <button className="btn-secondary" onClick={() => share.mutate(d.id)}>Compartir</button>
              </div>
            </header>
            {d.share_token && (
              <p className="text-xs text-gray-500 mt-2">
                Compartido: <code>/share/{d.share_token}</code>
              </p>
            )}
          </li>
        ))}
        {list.data?.length === 0 && <li className="text-gray-500">Aún no has generado documentos.</li>}
      </ul>
    </div>
  );
}
