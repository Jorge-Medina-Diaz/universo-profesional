import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { universe } from "@/shared/api";
import { SuggestionBar } from "@/widgets/SuggestionBar";

const SECTIONS = [
  { key: "education", label: "Educación" },
  { key: "experience", label: "Experiencia" },
  { key: "project", label: "Proyectos" },
  { key: "skill", label: "Competencias" },
  { key: "certification", label: "Certificaciones" },
  { key: "course", label: "Cursos" },
  { key: "language", label: "Idiomas" },
  { key: "achievement", label: "Logros" },
] as const;

export function UniversePage() {
  const { t } = useTranslation();
  const summaryQuery = useQuery({
    queryKey: ["universe", "summary"],
    queryFn: () => universe.summary(),
  });

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 pb-24 md:pb-8 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl md:text-3xl font-bold">{t("universe.title")}</h1>
        <div className="flex gap-2">
          <a href="#/connections" className="btn-secondary text-xs">🔗 Conexiones</a>
          <a href="#/cv/new" className="btn-primary">{t("cv.generate")}</a>
        </div>
      </header>

      <SuggestionBar />

      {summaryQuery.data && (
        <section className="card">
          <h2 className="text-lg font-semibold mb-3">{t("universe.summary")}</h2>
          <div className="grid grid-cols-5 gap-3 text-center">
            {(["educations", "experiences", "projects", "skills", "languages"] as const).map((k) => (
              <div key={k}>
                <div className="text-2xl font-bold">{summaryQuery.data!.counts[k]}</div>
                <div className="text-xs text-gray-500 capitalize">{k}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {SECTIONS.map((s) => (
        <Section key={s.key} kind={s.key} label={s.label} />
      ))}
    </div>
  );
}

function Section({ kind, label }: { kind: string; label: string }) {
  const qc = useQueryClient();
  const listQuery = useQuery({ queryKey: ["universe", kind], queryFn: () => universe.list(kind) });
  const [open, setOpen] = useState(false);
  const remove = useMutation({
    mutationFn: (id: string) => universe.remove(kind, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["universe", kind] }),
  });

  return (
    <section className="card">
      <header className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">{label}</h2>
        <button className="btn-secondary" onClick={() => setOpen((o) => !o)}>
          {open ? "Cerrar" : "+ Añadir"}
        </button>
      </header>
      {open && <AddForm kind={kind} onDone={() => { setOpen(false); qc.invalidateQueries({ queryKey: ["universe", kind] }); qc.invalidateQueries({ queryKey: ["universe", "summary"] }); }} />}
      <ul className="divide-y divide-gray-100">
        {listQuery.isLoading && <li className="py-2 text-sm text-gray-500">Cargando…</li>}
        {listQuery.data?.length === 0 && (
          <li className="py-3 text-sm text-gray-500">Aún sin entradas.</li>
        )}
        {listQuery.data?.map((row) => (
          <li key={row.id as string} className="py-3 flex items-start justify-between gap-3">
            <div className="text-sm">{summarize(kind, row)}</div>
            <button
              className="text-xs text-red-600 hover:underline"
              onClick={() => remove.mutate(row.id as string)}
            >
              borrar
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function summarize(kind: string, row: Record<string, unknown>): string {
  if (kind === "education") return `${row.degree ?? ""} — ${row.institution} (${row.start_date ?? ""}–${row.end_date ?? row.is_current ? "actual" : ""})`;
  if (kind === "experience") return `${row.role} @ ${row.organization} (${row.start_date ?? ""}–${row.end_date ?? "actual"})`;
  if (kind === "project") return `${row.name} — ${(row.tech_stack as unknown[] | undefined)?.join(", ") ?? ""}`;
  if (kind === "skill") return `${row.name} · ${row.category}${row.level ? " · " + row.level : ""}`;
  if (kind === "certification") return `${row.name} — ${row.issuer ?? ""}`;
  if (kind === "course") return `${row.title} — ${row.platform ?? ""}`;
  if (kind === "language") return `${row.name} (${row.level})`;
  if (kind === "achievement") return `${row.title}`;
  return JSON.stringify(row);
}

function AddForm({ kind, onDone }: { kind: string; onDone: () => void }) {
  const [body, setBody] = useState<Record<string, unknown>>({});
  const fields = FIELDS[kind] ?? [];
  const add = useMutation({
    mutationFn: () => universe.add(kind, body),
    onSuccess: onDone,
  });
  return (
    <form
      className="grid md:grid-cols-2 gap-3 mb-4"
      onSubmit={(e) => {
        e.preventDefault();
        add.mutate();
      }}
    >
      {fields.map((f) => (
        <div key={f.name}>
          <label className="label" htmlFor={`${kind}-${f.name}`}>{f.label}</label>
          {f.type === "textarea" ? (
            <textarea id={`${kind}-${f.name}`} className="input" onChange={(e) => setBody((b) => ({ ...b, [f.name]: e.target.value }))} />
          ) : (
            <input id={`${kind}-${f.name}`} type={f.type} className="input" onChange={(e) => setBody((b) => ({ ...b, [f.name]: f.type === "number" ? Number(e.target.value) : e.target.value }))} />
          )}
        </div>
      ))}
      <div className="md:col-span-2 flex gap-2 justify-end">
        <button type="submit" className="btn-primary" disabled={add.isPending}>
          {add.isPending ? "Guardando…" : "Guardar"}
        </button>
      </div>
      {add.isError && <p className="md:col-span-2 text-sm text-red-600">{(add.error as Error).message}</p>}
    </form>
  );
}

type Field = { name: string; label: string; type: "text" | "date" | "number" | "textarea" };

const FIELDS: Record<string, Field[]> = {
  education: [
    { name: "institution", label: "Institución", type: "text" },
    { name: "degree", label: "Título", type: "text" },
    { name: "field_of_study", label: "Especialidad", type: "text" },
    { name: "start_date", label: "Fecha inicio", type: "date" },
    { name: "end_date", label: "Fecha fin", type: "date" },
  ],
  experience: [
    { name: "organization", label: "Organización", type: "text" },
    { name: "role", label: "Puesto", type: "text" },
    { name: "start_date", label: "Fecha inicio", type: "date" },
    { name: "end_date", label: "Fecha fin", type: "date" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
  project: [
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
    { name: "url", label: "URL", type: "text" },
  ],
  skill: [
    { name: "name", label: "Nombre", type: "text" },
    { name: "category", label: "Categoría (hard, soft, tool, methodology)", type: "text" },
    { name: "level", label: "Nivel (basic, intermediate, high, expert)", type: "text" },
    { name: "years", label: "Años", type: "number" },
  ],
  certification: [
    { name: "name", label: "Nombre", type: "text" },
    { name: "issuer", label: "Emisor", type: "text" },
    { name: "issued_on", label: "Fecha", type: "date" },
  ],
  course: [
    { name: "title", label: "Título", type: "text" },
    { name: "platform", label: "Plataforma", type: "text" },
  ],
  language: [
    { name: "code", label: "Código ISO 639-1 (ej. es, en)", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "level", label: "Nivel CEFR (A1..C2, native)", type: "text" },
  ],
  achievement: [
    { name: "title", label: "Título", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
};
