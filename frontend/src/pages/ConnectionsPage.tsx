/**
 * One-stop page to wire all import sources for the universe:
 *   GitHub OAuth · LinkedIn ZIP · CV PDF.
 *
 * After connecting, the user can trigger sync / re-sync; status badges show
 * last sync timestamp + error if any. PDF/LinkedIn upload show a parsed
 * preview before committing.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { integrations } from "@/shared/api-extra";

export function ConnectionsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const conns = useQuery({
    queryKey: ["connections"],
    queryFn: () => integrations.list(),
  });
  const runs = useQuery({
    queryKey: ["syncRuns"],
    queryFn: () => integrations.syncRuns(5),
  });

  // Handle ?connected=github&error=... from OAuth callback redirect
  const [flash, setFlash] = useState<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
    if (params.get("connected")) {
      setFlash(`Conectado: ${params.get("connected")}`);
      qc.invalidateQueries({ queryKey: ["connections"] });
    } else if (params.get("error")) {
      setFlash(`Error: ${decodeURIComponent(params.get("error") || "")}`);
    }
  }, [qc]);

  const ghAuthorize = useMutation({
    mutationFn: () => integrations.github.authorizeUrl(),
    onSuccess: (r) => {
      window.location.href = r.authorize_url;
    },
  });
  const ghSync = useMutation({
    mutationFn: () => integrations.github.sync(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      qc.invalidateQueries({ queryKey: ["universe"] });
      qc.invalidateQueries({ queryKey: ["syncRuns"] });
    },
  });
  const ghDisconnect = useMutation({
    mutationFn: () => integrations.github.disconnect(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const conn = (provider: string) =>
    conns.data?.connections.find((c) => c.provider === provider);

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 pb-24 md:pb-6 space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Conexiones</h1>
        <p className="text-sm text-gray-600">
          Conecta tus cuentas para construir tu universo en minutos. No reescribimos lo
          que ya tienes — lo absorbemos.
        </p>
      </header>

      {flash && (
        <div role="status" className="rounded-md border border-brand-200 bg-brand-50 px-3 py-2 text-sm">
          {flash}
        </div>
      )}

      <ProviderCard
        title="GitHub"
        emoji="🐙"
        description="Repos, lenguajes, pinned, contributions y organizaciones se convierten en proyectos, skills, intereses y experiencias."
        connection={conn("github")}
        onConnect={() => ghAuthorize.mutate()}
        onSync={() => ghSync.mutate()}
        onDisconnect={() => ghDisconnect.mutate()}
        connectLabel="Conectar con GitHub"
        connectPending={ghAuthorize.isPending}
        syncPending={ghSync.isPending}
      />

      <LinkedInCard />

      <PdfCard />

      <section className="card">
        <h2 className="font-semibold text-sm mb-2">Últimas sincronizaciones</h2>
        {runs.data?.runs.length ? (
          <ul className="space-y-2 text-sm">
            {runs.data.runs.map((r: any) => (
              <li key={r.id} className="flex items-start justify-between gap-3">
                <div>
                  <p>
                    <span className="font-medium">{r.provider}</span>{" "}
                    <span className={r.ok ? "text-green-700" : "text-red-600"}>
                      {r.ok === null ? "…" : r.ok ? "ok" : "error"}
                    </span>
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(r.started_at).toLocaleString()} ·{" "}
                    +{r.items_created} / ~{r.items_updated}
                    {r.error ? ` · ${r.error}` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-gray-500">Aún no has sincronizado.</p>
        )}
      </section>
    </div>
  );
}

function ProviderCard({
  title,
  emoji,
  description,
  connection,
  onConnect,
  onSync,
  onDisconnect,
  connectLabel,
  connectPending,
  syncPending,
}: {
  title: string;
  emoji: string;
  description: string;
  connection: any;
  onConnect: () => void;
  onSync?: () => void;
  onDisconnect?: () => void;
  connectLabel: string;
  connectPending?: boolean;
  syncPending?: boolean;
}) {
  const connected = !!connection;
  return (
    <section className="card">
      <header className="flex items-start gap-3">
        <span aria-hidden className="text-2xl leading-none">
          {emoji}
        </span>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold">{title}</h2>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
        {connected && (
          <span className="badge-brand whitespace-nowrap">conectado</span>
        )}
      </header>
      {connected && (
        <p className="text-xs text-gray-500 mt-2">
          {connection.username && <>@{connection.username} · </>}
          {connection.last_synced_at
            ? `sync ${new Date(connection.last_synced_at).toLocaleString()}`
            : "aún sin sync"}
          {connection.sync_status === "error" && (
            <span className="text-red-600"> · error: {connection.sync_error}</span>
          )}
        </p>
      )}
      <div className="mt-3 flex gap-2 flex-wrap">
        {!connected && (
          <button className="btn-primary" onClick={onConnect} disabled={connectPending}>
            {connectPending ? "Abriendo…" : connectLabel}
          </button>
        )}
        {connected && onSync && (
          <button className="btn-primary" onClick={onSync} disabled={syncPending}>
            {syncPending ? "Sincronizando…" : "Sincronizar ahora"}
          </button>
        )}
        {connected && onDisconnect && (
          <button className="btn-secondary" onClick={onDisconnect}>
            Desconectar
          </button>
        )}
      </div>
    </section>
  );
}

function LinkedInCard() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<any | null>(null);
  const [sid, setSid] = useState<string | null>(null);

  const parseUpload = useMutation({
    mutationFn: (f: File) => integrations.linkedin.parseZip(f),
    onSuccess: (r) => {
      setParsed(r.parsed);
      setSid(r.session_id);
    },
  });
  const commit = useMutation({
    mutationFn: (id: string) => integrations.linkedin.commit(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universe"] });
      setParsed(null);
      setSid(null);
    },
  });

  const counts = parsed
    ? Object.fromEntries(
        Object.entries(parsed).map(([k, v]: [string, any]) => [
          k,
          Array.isArray(v) ? v.length : 1,
        ]),
      )
    : null;

  return (
    <section className="card">
      <header className="flex items-start gap-3">
        <span aria-hidden className="text-2xl leading-none">in</span>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold">LinkedIn</h2>
          <p className="text-sm text-gray-600">
            Sube el ZIP de tu &laquo;Get a copy of your data&raquo; (17 CSVs).
            Parseamos posiciones, educación, skills, idiomas, certificaciones,
            honors, publicaciones, proyectos, cursos, voluntariado y patentes.
          </p>
        </div>
      </header>
      <div className="mt-3 flex gap-2 flex-wrap">
        <button
          className="btn-primary"
          onClick={() => inputRef.current?.click()}
          disabled={parseUpload.isPending}
        >
          {parseUpload.isPending ? "Procesando…" : "Subir ZIP"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) parseUpload.mutate(f);
          }}
        />
      </div>
      {counts && (
        <div className="mt-3 rounded border border-brand-200 bg-brand-50/30 p-3">
          <p className="text-xs text-gray-600 mb-2">Detectado:</p>
          <ul className="grid grid-cols-2 gap-y-1 text-xs">
            {Object.entries(counts).map(([k, n]) => (
              <li key={k}>
                <span className="text-gray-500">{k}:</span> {String(n)}
              </li>
            ))}
          </ul>
          <button
            className="btn-primary mt-3"
            onClick={() => sid && commit.mutate(sid)}
            disabled={commit.isPending}
          >
            {commit.isPending ? "Importando…" : "Importar todo"}
          </button>
        </div>
      )}
    </section>
  );
}

function PdfCard() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [parsed, setParsed] = useState<any | null>(null);
  const [sid, setSid] = useState<string | null>(null);
  const [selection, setSelection] = useState<Record<string, Set<number>>>({});

  const parseUpload = useMutation({
    mutationFn: (f: File) => integrations.pdf.parse(f),
    onSuccess: (r) => {
      setParsed(r.parsed);
      setSid(r.session_id);
      const sel: Record<string, Set<number>> = {};
      for (const [k, v] of Object.entries(r.parsed || {})) {
        if (Array.isArray(v)) sel[k] = new Set(v.map((_, i) => i));
      }
      setSelection(sel);
    },
  });
  const commit = useMutation({
    mutationFn: () => {
      const payload: Record<string, number[]> = {};
      for (const [k, set] of Object.entries(selection)) {
        payload[k] = [...set];
      }
      return integrations.pdf.commit(sid!, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universe"] });
      setParsed(null);
      setSid(null);
    },
  });

  const toggle = (section: string, idx: number) => {
    setSelection((prev) => {
      const next = { ...prev };
      const set = new Set(next[section] ?? []);
      if (set.has(idx)) set.delete(idx);
      else set.add(idx);
      next[section] = set;
      return next;
    });
  };

  return (
    <section className="card">
      <header className="flex items-start gap-3">
        <span aria-hidden className="text-2xl leading-none">📄</span>
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold">Importar CV (PDF)</h2>
          <p className="text-sm text-gray-600">
            Sube tu CV en PDF. Lo procesamos con un parser (LLM si está configurado, mock si no)
            y revisas qué entries añades.
          </p>
        </div>
      </header>
      <div className="mt-3 flex gap-2">
        <button
          className="btn-primary"
          onClick={() => inputRef.current?.click()}
          disabled={parseUpload.isPending}
        >
          {parseUpload.isPending ? "Analizando…" : "Subir PDF"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) parseUpload.mutate(f);
          }}
        />
      </div>
      {parsed && (
        <div className="mt-3 rounded border border-brand-200 bg-brand-50/30 p-3 space-y-3">
          {["experiences", "educations", "skills", "languages", "certifications", "projects", "achievements"].map((sec) => {
            const items = parsed[sec] as any[] | undefined;
            if (!items || items.length === 0) return null;
            return (
              <section key={sec}>
                <h3 className="text-xs font-semibold uppercase text-gray-500 mb-1">{sec}</h3>
                <ul className="space-y-1">
                  {items.map((it: any, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={selection[sec]?.has(i) ?? false}
                        onChange={() => toggle(sec, i)}
                        className="mt-0.5"
                      />
                      <span>
                        {summarize(sec, it)}
                        {it.confidence !== undefined && (
                          <span className="text-gray-400"> · {(it.confidence * 100).toFixed(0)}%</span>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
          <button
            className="btn-primary"
            onClick={() => commit.mutate()}
            disabled={commit.isPending}
          >
            {commit.isPending ? "Importando…" : "Importar seleccionados"}
          </button>
        </div>
      )}
    </section>
  );
}

function summarize(section: string, item: any): string {
  if (section === "experiences") return `${item.role} @ ${item.organization}`;
  if (section === "educations") return `${item.degree ?? ""} — ${item.institution}`;
  if (section === "skills") return `${item.name}${item.level ? ` (${item.level})` : ""}`;
  if (section === "languages") return `${item.name} (${item.level})`;
  if (section === "certifications") return `${item.name} — ${item.issuer ?? ""}`;
  if (section === "projects") return item.name;
  if (section === "achievements") return item.title;
  return JSON.stringify(item).slice(0, 100);
}
