/**
 * One-stop page to wire all import sources for the universe:
 *   GitHub OAuth · LinkedIn (OIDC + DMA + Bright Data + ZIP) · CV PDF.
 *
 * LinkedIn has 4 paths because LinkedIn's profile API was killed in 2018 and
 * each remaining option has tradeoffs:
 *   1. OIDC sign-in: identity only (no profile data), free.
 *   2. DMA 3rd-party API: full profile, free, EEA-only, needs LinkedIn approval.
 *   3. Bright Data: full profile, global, paid (PRO tier).
 *   4. ZIP fallback: full profile, free, requires manual user export.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { account, auth, useAuthStore } from "@/shared/api";
import { integrations, type Connection } from "@/shared/api-extra";
import {
  Badge,
  Button,
  Card,
  DropZone,
  Input,
  PageHeader,
  Reveal,
  Stagger,
  Surface,
  toast,
} from "@/ui";
import { GitHubIcon, LinkedInIcon } from "@/ui/icons";
import {
  ImportPreviewTable,
  type ImportPreviewSection,
  type ImportPreviewSelection,
} from "@/widgets/ImportPreviewTable";
import { queryKeys } from "@/shared/queryKeys";

interface SyncRun {
  id: string;
  provider: string;
  ok: boolean | null;
  started_at: string;
  items_created: number;
  items_updated: number;
  error?: string | null;
}

type ParsedImport = Record<string, unknown>;

export function ConnectionsPage() {
  useTranslation();
  const qc = useQueryClient();
  const conns = useQuery({
    queryKey: queryKeys.connections.all,
    queryFn: () => integrations.list(),
  });
  const runs = useQuery({
    queryKey: queryKeys.syncRuns.all,
    queryFn: () => integrations.syncRuns(5),
  });

  // Handle ?connected=github&error=... from OAuth callback redirect.
  // Filter out "linkedin_not_configured" — that's a dev sentinel, not user-facing.
  const [flash, setFlash] = useState<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split("?")[1] || "");
    if (params.get("connected")) {
      setFlash(`Conectado: ${params.get("connected")}`);
      qc.invalidateQueries({ queryKey: queryKeys.connections.all });
    } else if (params.get("error")) {
      const e = decodeURIComponent(params.get("error") || "");
      if (e !== "linkedin_not_configured") {
        setFlash(`Error: ${e}`);
      }
      // Clean the URL so a refresh doesn't repaint the flash
      window.history.replaceState(null, "", "#/connections");
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
      qc.invalidateQueries({ queryKey: queryKeys.connections.all });
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      qc.invalidateQueries({ queryKey: queryKeys.syncRuns.all });
    },
  });
  const ghDisconnect = useMutation({
    mutationFn: () => integrations.github.disconnect(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connections.all }),
  });

  const conn = (provider: string) =>
    conns.data?.connections.find((c) => c.provider === provider);

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Importar"
        title="Conexiones"
        subtitle="Conecta tus cuentas para construir tu universo en minutos. No reescribimos lo que ya tienes — lo absorbemos."
      />

      {flash && (
        <Reveal>
          <Card padding="sm" tone="surface" className="flex items-center gap-3 border border-leaf/30">
            <CheckCircle2 size={18} className="text-leaf-ink shrink-0" />
            <span className="text-sm text-ink">{flash}</span>
          </Card>
        </Reveal>
      )}

      <Stagger className="flex flex-col gap-4 md:gap-5" delayStep={0.05}>
        <ProviderCard
          title="GitHub"
          iconBg="bg-ink"
          iconColor="text-canvas"
          icon={<GitHubIcon size={20} />}
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
      </Stagger>

      <Card padding="lg">
        <h2 className="text-heading-sm font-medium tracking-tight mb-4">
          Últimas sincronizaciones
        </h2>
        {runs.data?.runs.length ? (
          <ul className="space-y-3">
            {(runs.data.runs as unknown as SyncRun[]).map((r) => (
              <li
                key={r.id}
                className="flex items-start justify-between gap-3 border-b border-ink/5 last:border-0 pb-3 last:pb-0"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ink capitalize">{r.provider}</span>
                    {r.ok === null ? (
                      <Badge tone="stone" size="sm" icon={<Loader2 size={10} className="animate-spin" />}>
                        en curso
                      </Badge>
                    ) : r.ok ? (
                      <Badge tone="leaf" size="sm" dot>
                        ok
                      </Badge>
                    ) : (
                      <Badge tone="danger" size="sm" icon={<AlertCircle size={10} />}>
                        error
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-stone mt-1">
                    {new Date(r.started_at).toLocaleString()} · +{r.items_created} / ~{r.items_updated}
                    {r.error ? ` · ${r.error}` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-stone">Aún no has sincronizado.</p>
        )}
      </Card>
    </Surface>
  );
}

function ProviderCard({
  title,
  icon,
  iconBg,
  iconColor,
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
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  description: string;
  connection: Connection | undefined;
  onConnect: () => void;
  onSync?: () => void;
  onDisconnect?: () => void;
  connectLabel: string;
  connectPending?: boolean;
  syncPending?: boolean;
}) {
  const connected = !!connection;
  return (
    <Card padding="lg">
      <header className="flex items-start gap-4">
        <span
          aria-hidden
          className={`inline-flex items-center justify-center w-12 h-12 rounded-full shrink-0 ${iconBg} ${iconColor}`}
        >
          {icon}
        </span>
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-heading-sm font-medium tracking-tight text-ink">{title}</h2>
            {connected ? (
              <Badge tone="leaf" dot>
                Conectado
              </Badge>
            ) : (
              <Badge tone="stone">Sin conectar</Badge>
            )}
          </div>
          <p className="text-sm text-stone leading-relaxed">{description}</p>
        </div>
      </header>
      {connected && (
        <p className="text-xs text-stone mt-3">
          {connection.username && <>@{connection.username} · </>}
          {connection.last_synced_at
            ? `Último sync: ${new Date(connection.last_synced_at).toLocaleString()}`
            : "aún sin sync"}
          {connection.sync_status === "error" && (
            <span className="text-danger"> · error: {connection.sync_error}</span>
          )}
        </p>
      )}
      <div className="mt-5 flex gap-2 flex-wrap">
        {!connected && (
          <Button onClick={onConnect} loading={connectPending}>
            {connectPending ? "Abriendo" : connectLabel}
          </Button>
        )}
        {connected && onSync && (
          <Button onClick={onSync} loading={syncPending}>
            {syncPending ? "Sincronizando" : "Sincronizar ahora"}
          </Button>
        )}
        {connected && onDisconnect && (
          <Button variant="ghost" onClick={onDisconnect}>
            Desconectar
          </Button>
        )}
      </div>
    </Card>
  );
}

function LinkedInCard() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: queryKeys.me.all, queryFn: () => auth.me() });
  const conns = useQuery({
    queryKey: queryKeys.connections.all,
    queryFn: () => integrations.list(),
  });
  const oidcConn = conns.data?.connections.find((c) => c.provider === "linkedin_oidc");
  const dmaConn = conns.data?.connections.find((c) => c.provider === "linkedin_dma");
  const isPro = me.data?.tier === "pro";

  // Probe LinkedIn capabilities — which paths talk to real APIs vs return a
  // fixture. Used to hide buttons that would 503 AND to label sample-data
  // buttons honestly so the user knows the difference between "your real
  // profile" and "the canned demo data".
  const linkedinProbe = useQuery({
    queryKey: queryKeys.linkedin.probe,
    queryFn: () => integrations.linkedin.oidcAuthorize(),
    staleTime: 60_000,
  });
  const linkedinStatus = useQuery({
    queryKey: queryKeys.linkedin.status,
    queryFn: () => integrations.linkedin.status(),
    staleTime: 60_000,
  });
  const linkedinConfigured = linkedinProbe.data?.configured ?? false;
  const dmaUsesFixture = linkedinStatus.data?.dma.uses_fixture ?? true;
  const brightdataUsesFixture = linkedinStatus.data?.brightdata.uses_fixture ?? true;

  // Shared state: any of the three paths can open an import session, then we
  // route through the same selection UI before committing.
  const [parsed, setParsed] = useState<ParsedImport | null>(null);
  const [sid, setSid] = useState<string | null>(null);
  const [parsedSource, setParsedSource] = useState<
    "zip" | "dma" | "brightdata" | null
  >(null);
  const [brightdataUrl, setBrightdataUrl] = useState("");
  const [brightdataFresh, setBrightdataFresh] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- OIDC (link to current authed user) ---
  const linkOidc = useMutation({
    mutationFn: async () => {
      const r = await integrations.linkedin.oidcAuthorize(
        useAuthStore.getState().userId ?? undefined,
      );
      if (!r.configured || !r.authorize_url) {
        throw new Error(
          "LinkedIn OAuth aún no está configurado en el backend (falta LINKEDIN_CLIENT_ID).",
        );
      }
      window.location.href = r.authorize_url;
    },
    onError: (e: unknown) => setError((e as Error)?.message ?? String(e)),
  });
  // --- DMA ---
  // Single Sync button — the backend's DMA provider falls back to a
  // deterministic fixture when no real token is stored, so the user never
  // has to navigate an "authorize first" gate in dev. If/when real LinkedIn
  // DMA credentials get wired up, we'll add a discreet upgrade CTA here.
  const dmaSync = useMutation({
    mutationFn: async () => {
      const r = await integrations.linkedin.dma.sync();
      return r;
    },
    onSuccess: (r) => {
      setError(null);
      setParsed(r.parsed);
      setSid(r.session_id);
      setParsedSource("dma");
    },
    onError: (e: unknown) => {
      const err = e as { status?: number; message?: string };
      setError(
        `Sync DMA falló (${err.status ?? "?"}): ${err.message ?? String(e)}`,
      );
    },
  });
  const dmaCommit = useMutation({
    mutationFn: ({ id, selection }: { id: string; selection?: Record<string, number[]> }) =>
      integrations.linkedin.dma.commit(id, selection),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      setParsed(null);
      setSid(null);
      setParsedSource(null);
      toast.success("Importado", "Tu universo se ha actualizado.");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos importar", (e as Error).message),
  });
  const dmaDisconnect = useMutation({
    mutationFn: () => integrations.linkedin.dma.disconnect(),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connections.all }),
  });

  // --- Bright Data ---
  const brightdataSync = useMutation({
    mutationFn: (body: { linkedin_url?: string; fresh?: boolean }) =>
      integrations.linkedin.brightdata.sync(body),
    onSuccess: (r) => {
      setError(null);
      setParsed(r.parsed);
      setSid(r.session_id);
      setParsedSource("brightdata");
    },
    onError: (e: unknown) => {
      const err = e as { status?: number; message?: string };
      if (err.status === 402) {
        setError("Esta función requiere el plan PRO.");
      } else {
        setError(err.message ?? String(e));
      }
    },
  });
  const brightdataCommit = useMutation({
    mutationFn: ({ id, selection }: { id: string; selection?: Record<string, number[]> }) =>
      integrations.linkedin.brightdata.commit(id, selection),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      setParsed(null);
      setSid(null);
      setParsedSource(null);
      toast.success("Importado", "Tu universo se ha actualizado.");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos importar", (e as Error).message),
  });
  const upgradePro = useMutation({
    mutationFn: () => account.setTier("pro"),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.me.all }),
  });

  // --- ZIP fallback ---
  const inputRef = useRef<HTMLInputElement>(null);
  const parseUpload = useMutation({
    mutationFn: (f: File) => integrations.linkedin.parseZip(f),
    onSuccess: (r) => {
      setParsed(r.parsed);
      setSid(r.session_id);
      setParsedSource("zip");
    },
  });
  const zipCommit = useMutation({
    mutationFn: (id: string) => integrations.linkedin.commitZip(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      setParsed(null);
      setSid(null);
      setParsedSource(null);
    },
  });

  const onCommit = (sel?: ImportPreviewSelection) => {
    if (!sid) return;
    const selection = sel ? toSectionMap(sel) : undefined;
    if (parsedSource === "dma") dmaCommit.mutate({ id: sid, selection });
    else if (parsedSource === "brightdata")
      brightdataCommit.mutate({ id: sid, selection });
    else if (parsedSource === "zip") zipCommit.mutate(sid);
  };
  const commitPending =
    dmaCommit.isPending || brightdataCommit.isPending || zipCommit.isPending;
  const previewSections = parsed ? buildLinkedInSections(parsed) : [];

  // Live status — surfaces in-flight mutations, last error, last success so the
  // user never has to guess "did anything happen?". Pulls from every LinkedIn
  // path because only one can be active at a time.
  const liveStatus = (() => {
    if (dmaSync.isPending) return { tone: "info" as const, msg: "Sincronizando vía LinkedIn DMA…" };
    if (brightdataSync.isPending) return { tone: "info" as const, msg: "Buscando tu perfil real en LinkedIn vía Bright Data (puede tardar hasta 90 s)…" };
    if (parseUpload.isPending) return { tone: "info" as const, msg: "Procesando ZIP de LinkedIn…" };
    if (dmaCommit.isPending || brightdataCommit.isPending || zipCommit.isPending)
      return { tone: "info" as const, msg: "Importando entradas en tu universo…" };
    if (error) return { tone: "error" as const, msg: error };
    if (parsed && parsedSource) {
      const total = Object.values(parsed)
        .filter((v): v is unknown[] => Array.isArray(v))
        .reduce((s, v) => s + v.length, 0);
      return {
        tone: "success" as const,
        msg: `${total} entradas detectadas — revisa abajo y pulsa Importar todo.`,
      };
    }
    return null;
  })();

  return (
    <Card padding="lg">
      <header className="flex items-start gap-4">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-ink text-canvas shrink-0"
        >
          <LinkedInIcon size={20} />
        </span>
        <div className="flex-1 min-w-0 space-y-1">
          <h2 className="text-heading-sm font-medium tracking-tight text-ink">LinkedIn</h2>
          <p className="text-sm text-stone leading-relaxed">
            Trae tu experiencia, educación, skills, certificaciones y proyectos
            sin reescribir nada.
          </p>
        </div>
      </header>

      {liveStatus && (
        <div
          role={liveStatus.tone === "error" ? "alert" : "status"}
          className={`mt-3 rounded-md px-3 py-2 text-xs flex items-start gap-2 ${
            liveStatus.tone === "error"
              ? "bg-danger-soft border border-danger/30 text-danger-ink"
              : liveStatus.tone === "success"
                ? "bg-leaf-soft border border-leaf/30 text-leaf-ink"
                : "bg-sunbeam-soft border border-sunbeam/40 text-sunbeam-ink"
          }`}
        >
          {liveStatus.tone === "info" && (
            <span
              aria-hidden
              className="inline-block w-3 h-3 rounded-full border-2 border-sunbeam-ink border-r-transparent animate-spin"
            />
          )}
          <span className="flex-1">{liveStatus.msg}</span>
          {liveStatus.tone === "error" && (
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-danger hover:underline"
              aria-label="Cerrar"
            >
              ×
            </button>
          )}
        </div>
      )}

      {/* Path A — OIDC: identity + future DMA upgrade. Hidden entirely when
          LinkedIn OAuth isn't configured (no LINKEDIN_CLIENT_ID), since the
          button would only 503 and confuse the user. */}
      {linkedinConfigured && (
        <div className="mt-3 border-t pt-3 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium">Vincular cuenta</p>
              <p className="text-xs text-stone">
                Para auto-rellenar nombre, email y foto, y habilitar las
                sincronizaciones avanzadas.
              </p>
            </div>
            {oidcConn ? (
              <Badge tone="leaf" dot className="whitespace-nowrap">
                vinculada
              </Badge>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                className="whitespace-nowrap"
                onClick={() => linkOidc.mutate()}
                loading={linkOidc.isPending}
              >
                Vincular LinkedIn
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Path B — DMA (free, EEA). In dev (no LinkedIn creds), this returns a
          fixture, so we label the button honestly. */}
      <div className="mt-3 border-t pt-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <p className="text-sm font-medium">
              {dmaUsesFixture ? (
                <>
                  Probar el flujo con <span className="text-sunbeam-ink">datos de muestra</span>
                </>
              ) : (
                <>
                  Sincronizar perfil completo · <span className="text-leaf-ink">gratis · UE</span>
                </>
              )}
            </p>
            <p className="text-xs text-stone">
              {dmaUsesFixture
                ? "Hoy esto NO trae tu perfil real — devuelve datos de ejemplo para que veas cómo funciona la UI. Para datos reales, sube tu ZIP (abajo) o pásate a PRO."
                : "Trae tu experiencia, educación, skills, certificaciones y proyectos directos desde LinkedIn (DMA oficial)."}
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <Button
            variant={dmaUsesFixture ? "secondary" : "primary"}
            onClick={() => dmaSync.mutate()}
            loading={dmaSync.isPending}
          >
            {dmaSync.isPending
              ? "Sincronizando…"
              : dmaUsesFixture
                ? "Probar con datos de muestra"
                : "Sincronizar perfil"}
          </Button>
          {dmaConn && (
            <button
              className="text-xs text-stone hover:text-danger underline"
              onClick={() => dmaDisconnect.mutate()}
            >
              Revocar
            </button>
          )}
        </div>
        {dmaConn?.last_synced_at && (
          <p className="text-xs text-stone">
            Última sync: {new Date(dmaConn.last_synced_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Path C — Bright Data (PRO, global). When no API key is configured we
          tell the user honestly that the lookup will fall back to a fixture. */}
      <div className="mt-3 border-t pt-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <p className="text-sm font-medium">
              {brightdataUsesFixture ? (
                <>
                  Bright Data <span className="text-sunbeam-ink">sin API key</span> · devuelve fixture
                </>
              ) : (
                <>
                  Sincronizar perfil completo · <span className="text-sunbeam-ink">PRO · global</span>
                </>
              )}
            </p>
            <p className="text-xs text-stone">
              {brightdataUsesFixture ? (
                <>
                  Para perfiles reales necesitas una API key de Bright Data.
                  Regístrate en{" "}
                  <a
                    href="https://brightdata.com/cp/signup"
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 hover:underline font-medium"
                  >
                    brightdata.com/cp/signup
                  </a>{" "}
                  y pasa la key al backend via <code className="bg-surface px-1 rounded">BRIGHTDATA_API_KEY</code>.
                </>
              ) : (
                <>
                  Pega tu URL pública de LinkedIn y traemos tu perfil completo
                  (acerca de, experiencia con descripciones, skills, certificaciones,
                  idiomas, cursos, logros, publicaciones, proyectos…). Tarda 30-90 s
                  la primera vez (lookup fresco), instantáneo si está cacheado.
                </>
              )}
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <Input
            type="url"
            placeholder="https://www.linkedin.com/in/tu-usuario"
            value={brightdataUrl}
            onChange={(e) => setBrightdataUrl(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          {isPro ? (
            <Button
              size="sm"
              className="whitespace-nowrap"
              onClick={() =>
                brightdataSync.mutate({
                  linkedin_url: brightdataUrl.trim() || undefined,
                  fresh: brightdataFresh,
                })
              }
              loading={brightdataSync.isPending}
            >
              {brightdataSync.isPending ? "Buscando…" : "Importar (PRO)"}
            </Button>
          ) : (
            <Button
              variant="cta"
              size="sm"
              className="whitespace-nowrap"
              onClick={() => upgradePro.mutate()}
              loading={upgradePro.isPending}
              title="En producción este botón llevaría a Stripe. En dev: activa PRO directamente."
            >
              {upgradePro.isPending ? "Activando…" : "Pasar a PRO (dev)"}
            </Button>
          )}
        </div>
        {isPro && (
          <label className="text-xs text-stone inline-flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={brightdataFresh}
              onChange={(e) => setBrightdataFresh(e.target.checked)}
              className="rounded"
            />
            <span>
              Forzar lookup fresco — bypass del cache de Bright Data (~$0.50-1 vs $0.10).
              Úsalo solo si cambiaste recientemente tu visibilidad en LinkedIn.
            </span>
          </label>
        )}
      </div>

      {/* Path D — ZIP. When no real LinkedIn API is configured, this is the
          ONLY path that brings real user data, so we promote it visually. */}
      <div
        className={`mt-3 border-t pt-3 space-y-2 ${
          dmaUsesFixture && brightdataUsesFixture ? "bg-leaf-soft/40 -mx-4 px-4 py-3 rounded" : ""
        }`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <p className="text-sm font-medium">
              {dmaUsesFixture && brightdataUsesFixture && (
                <span className="inline-block bg-leaf text-ink text-[10px] px-1.5 py-0.5 rounded mr-2 uppercase font-medium">
                  Recomendado
                </span>
              )}
              Subir ZIP de tu export de LinkedIn ·{" "}
              <span className="text-leaf-ink">gratis · datos reales</span>
            </p>
            <p className="text-xs text-stone leading-relaxed">
              <strong>Esta es la única forma de importar tu perfil real ahora mismo.</strong>
              {" "}Pide a LinkedIn una copia de tus datos en{" "}
              <a
                href="https://www.linkedin.com/mypreferences/d/download-my-data"
                className="text-brand-700 hover:underline font-medium"
                target="_blank"
                rel="noreferrer"
              >
                Settings → Get a copy of your data
              </a>
              . LinkedIn tarda 10 min – 24 h en enviarte el ZIP por email.
              Cuando llegue, súbelo aquí y parseamos tus posiciones, educación,
              skills, certificaciones, honors, publicaciones, proyectos, cursos
              y voluntariado.
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={dmaUsesFixture && brightdataUsesFixture ? "primary" : "secondary"}
            size={dmaUsesFixture && brightdataUsesFixture ? "md" : "sm"}
            onClick={() => inputRef.current?.click()}
            loading={parseUpload.isPending}
          >
            {parseUpload.isPending ? "Procesando…" : "Subir ZIP de LinkedIn"}
          </Button>
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
      </div>

      {parsed && parsedSource && previewSections.length > 0 && (
        <div className="mt-4">
          <ImportPreviewTable
            sections={previewSections}
            pending={commitPending}
            onCommit={onCommit}
            onCancel={() => {
              setParsed(null);
              setSid(null);
              setParsedSource(null);
            }}
            source={
              parsedSource === "dma"
                ? "linkedin-dma"
                : parsedSource === "brightdata"
                  ? "linkedin-brightdata"
                  : "linkedin-zip"
            }
          />
        </div>
      )}
    </Card>
  );
}

function toSectionMap(sel: ImportPreviewSelection): Record<string, number[]> {
  return { ...sel };
}

function buildLinkedInSections(parsed: ParsedImport): ImportPreviewSection[] {
  const defs: Array<[string, string, (r: Record<string, unknown>) => string, ((r: Record<string, unknown>) => string | undefined)?]> = [
    [
      "experiences",
      "Experiencias",
      (r) => `${(r.role as string | undefined) ?? "?"} @ ${(r.organization as string | undefined) ?? "?"}`,
      (r) => formatRange(r.start_date as string | null | undefined, r.end_date as string | null | undefined, r.is_current as boolean | undefined),
    ],
    [
      "educations",
      "Educación",
      (r) => `${(r.degree as string | undefined) ?? (r.field_of_study as string | undefined) ?? "?"} — ${(r.institution as string | undefined) ?? "?"}`,
      (r) => formatRange(r.start_date as string | null | undefined, r.end_date as string | null | undefined, r.is_current as boolean | undefined),
    ],
    ["skills", "Skills", (r) => `${r.name as string | undefined}${(r.level as string | undefined) ? ` · ${r.level as string}` : ""}`],
    ["languages", "Idiomas", (r) => `${r.name as string | undefined} (${(r.level as string | undefined) ?? "?"})`],
    [
      "certifications",
      "Certificaciones",
      (r) => `${r.name as string | undefined} — ${(r.issuer as string | undefined) ?? ""}`,
      (r) => ((r.issued_on as string | undefined) ? `Emitida ${r.issued_on as string}` : undefined),
    ],
    ["projects", "Proyectos", (r) => `${(r.name as string | undefined) ?? "?"}`],
    ["achievements", "Logros", (r) => `${(r.title as string | undefined) ?? "?"}`],
    ["courses", "Cursos", (r) => `${(r.title as string | undefined) ?? "?"}${(r.platform as string | undefined) ? ` · ${r.platform as string}` : ""}`],
  ];
  const sections: ImportPreviewSection[] = [];
  for (const [key, label, summarize, sublabel] of defs) {
    const rows = (parsed[key] as Array<Record<string, unknown>> | undefined) ?? [];
    if (rows.length > 0) {
      sections.push({ key, label, rows, summarize, sublabel });
    }
  }
  return sections;
}

function formatRange(start?: string | null, end?: string | null, isCurrent?: boolean): string | undefined {
  if (!start && !end && !isCurrent) return undefined;
  const a = start ? new Date(start).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "?";
  const b = isCurrent
    ? "Actual"
    : end
      ? new Date(end).toLocaleDateString(undefined, { month: "short", year: "numeric" })
      : "?";
  return `${a} — ${b}`;
}

function PdfCard() {
  const qc = useQueryClient();
  const [parsed, setParsed] = useState<ParsedImport | null>(null);
  const [sid, setSid] = useState<string | null>(null);

  const parseUpload = useMutation({
    mutationFn: (f: File) => integrations.pdf.parse(f),
    onSuccess: (r) => {
      setParsed(r.parsed);
      setSid(r.session_id);
    },
    onError: (e: unknown) =>
      toast.error("No pudimos parsear el PDF", (e as Error).message),
  });
  const commit = useMutation({
    mutationFn: (selection: Record<string, number[]>) =>
      integrations.pdf.commit(sid!, selection),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.universe.all });
      setParsed(null);
      setSid(null);
      toast.success("PDF importado", "Tu universo se ha actualizado.");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos importar", (e as Error).message),
  });

  const previewSections = parsed ? buildPdfSections(parsed) : [];

  return (
    <Card padding="lg">
      <header className="flex items-start gap-4">
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sunbeam text-sunbeam-ink shrink-0"
        >
          <span className="text-xl">📄</span>
        </span>
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-heading-sm font-medium tracking-tight text-ink">
              Importar CV (PDF)
            </h2>
            {parsed && (
              <Badge tone="leaf" dot>
                Parseado
              </Badge>
            )}
          </div>
          <p className="text-sm text-stone leading-relaxed">
            Sube tu CV en PDF. Lo procesamos con un parser (LLM si está configurado,
            mock si no) y revisas qué entries añades.
          </p>
        </div>
      </header>
      <div className="mt-5">
        <DropZone
          accept="application/pdf,.pdf"
          label={parseUpload.isPending ? "Analizando…" : "Arrastra tu CV en PDF"}
          hint="Hasta 10 MB. Parseamos secciones y revisas qué entries añades."
          loading={parseUpload.isPending}
          maxBytes={10 * 1024 * 1024}
          onFiles={(files) => parseUpload.mutate(files[0])}
          onError={(msg) => toast.error("PDF no aceptado", msg)}
        />
      </div>
      {parsed && previewSections.length > 0 && (
        <div className="mt-4">
          <ImportPreviewTable
            sections={previewSections}
            pending={commit.isPending}
            onCommit={(sel) => commit.mutate(toSectionMap(sel))}
            onCancel={() => {
              setParsed(null);
              setSid(null);
            }}
            source="pdf"
          />
        </div>
      )}
    </Card>
  );
}

function buildPdfSections(parsed: ParsedImport): ImportPreviewSection[] {
  const defs: Array<[string, string, (r: Record<string, unknown>) => string, ((r: Record<string, unknown>) => string | undefined)?]> = [
    [
      "experiences",
      "Experiencias",
      (r) => `${(r.role as string | undefined) ?? "?"} @ ${(r.organization as string | undefined) ?? "?"}`,
      (r) =>
        [
          formatRange(r.start_date as string | null | undefined, r.end_date as string | null | undefined, r.is_current as boolean | undefined),
          (r.confidence as number | undefined) !== undefined ? `${Math.round((r.confidence as number) * 100)}% confianza` : undefined,
        ]
          .filter(Boolean)
          .join(" · "),
    ],
    [
      "educations",
      "Educación",
      (r) => `${(r.degree as string | undefined) ?? (r.field_of_study as string | undefined) ?? "?"} — ${(r.institution as string | undefined) ?? "?"}`,
      (r) => formatRange(r.start_date as string | null | undefined, r.end_date as string | null | undefined, r.is_current as boolean | undefined),
    ],
    ["skills", "Skills", (r) => `${r.name as string | undefined}${(r.level as string | undefined) ? ` · ${r.level as string}` : ""}`],
    ["languages", "Idiomas", (r) => `${r.name as string | undefined} (${(r.level as string | undefined) ?? "?"})`],
    ["certifications", "Certificaciones", (r) => `${r.name as string | undefined} — ${(r.issuer as string | undefined) ?? ""}`],
    ["projects", "Proyectos", (r) => `${(r.name as string | undefined) ?? "?"}`],
    ["achievements", "Logros", (r) => `${(r.title as string | undefined) ?? "?"}`],
  ];
  const sections: ImportPreviewSection[] = [];
  for (const [key, label, summarize, sublabel] of defs) {
    const rows = (parsed[key] as Array<Record<string, unknown>> | undefined) ?? [];
    if (rows.length > 0) {
      sections.push({ key, label, rows, summarize, sublabel });
    }
  }
  return sections;
}

