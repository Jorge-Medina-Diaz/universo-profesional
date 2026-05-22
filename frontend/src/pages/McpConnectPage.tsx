import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Copy, Check, Terminal, ShieldCheck, Sparkles } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  PageHeader,
  Stagger,
  Surface,
  cn,
} from "@/ui";

type ClientId = "claude" | "codex" | "cursor" | "windsurf";

interface Client {
  id: ClientId;
  name: string;
  command: (endpoint: string) => string;
  notes?: string;
}

const CLIENTS: Client[] = [
  {
    id: "claude",
    name: "Claude Code / Desktop",
    command: (e) => `claude mcp add --transport http cvs-saas ${e}`,
    notes: "Se abrirá el navegador para completar el flujo OAuth.",
  },
  {
    id: "codex",
    name: "Codex (OpenAI)",
    command: (e) => `codex mcp add cvs-saas ${e}`,
  },
  {
    id: "cursor",
    name: "Cursor",
    command: (e) => `# .cursor/mcp.json
{
  "mcpServers": {
    "cvs-saas": { "url": "${e}" }
  }
}`,
  },
  {
    id: "windsurf",
    name: "Windsurf / Zed",
    command: (e) => `Endpoint: ${e}
Transport: streamable-http
Auth: oauth2.1 (DCR)`,
  },
];

const TOOLS = [
  { name: "get_profile", desc: "Lee tu universo profesional" },
  { name: "get_universe_summary", desc: "Resumen compacto del universo" },
  { name: "add_experience / update_experience", desc: "Mutaciones de experiencia" },
  { name: "add_skill / list_skills", desc: "Skills, derivados y evidencia" },
  { name: "match_job_to_profile", desc: "Score JD ↔ universo" },
  { name: "generate_cv", desc: "CV adaptado a una oferta (PDF/DOCX/JSON)" },
];

export function McpConnectPage() {
  const { t } = useTranslation();
  const base = window.location.origin;
  const endpoint = `${base}/mcp`;
  const [tab, setTab] = useState<ClientId>("claude");
  const active = CLIENTS.find((c) => c.id === tab) ?? CLIENTS[0];

  return (
    <Surface width="lg" spacing="md">
      <PageHeader
        eyebrow="Integraciones"
        title={t("mcp.title")}
        subtitle={t("mcp.intro")}
      />

      <Stagger className="flex flex-col gap-4 md:gap-6" delayStep={0.05}>
        <Card padding="lg">
          <div className="flex items-center gap-3 mb-3">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-canvas text-ink"
            >
              <Terminal size={16} />
            </span>
            <h2 className="text-heading-sm font-medium tracking-tight">
              {t("mcp.endpoint")}
            </h2>
          </div>
          <CopyableCode value={endpoint} />
          <div className="flex items-center gap-2 mt-3 text-xs text-stone">
            <ShieldCheck size={14} className="text-leaf-ink" />
            <span>
              Auth: OAuth 2.1 + PKCE + DCR. Metadatos en{" "}
              <a
                className="underline hover:text-ink transition-colors"
                href="/.well-known/oauth-authorization-server"
                target="_blank"
                rel="noreferrer"
              >
                /.well-known/oauth-authorization-server
              </a>
            </span>
          </div>
        </Card>

        <Card padding="lg">
          <h2 className="text-heading-sm font-medium tracking-tight mb-4">
            Conecta tu cliente
          </h2>
          <div role="tablist" className="relative flex flex-wrap gap-1 mb-5 border-b border-ink/8">
            {CLIENTS.map((c) => {
              const isActive = c.id === tab;
              return (
                <button
                  key={c.id}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setTab(c.id)}
                  className={cn(
                    "relative px-3 py-2.5 text-sm font-medium transition-colors duration-180 ease-pirsch -mb-px",
                    isActive ? "text-ink" : "text-stone hover:text-ink",
                  )}
                >
                  {c.name}
                  {isActive && (
                    <span
                      aria-hidden
                      className="absolute left-3 right-3 -bottom-px h-[2px] bg-leaf rounded-full"
                    />
                  )}
                </button>
              );
            })}
          </div>
          <CopyableCode value={active.command(endpoint)} multiline />
          {active.notes && (
            <p className="text-xs text-stone mt-3">{active.notes}</p>
          )}
        </Card>

        <Card padding="lg">
          <div className="flex items-center gap-3 mb-4">
            <span
              aria-hidden
              className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sunbeam-soft text-sunbeam-ink"
            >
              <Sparkles size={16} />
            </span>
            <h2 className="text-heading-sm font-medium tracking-tight">
              Herramientas disponibles
            </h2>
          </div>
          <ul className="grid sm:grid-cols-2 gap-2.5">
            {TOOLS.map((tool) => (
              <li
                key={tool.name}
                className="flex flex-col gap-0.5 rounded-card bg-canvas p-3"
              >
                <code className="text-sm font-medium text-ink">{tool.name}</code>
                <span className="text-xs text-stone">{tool.desc}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 pt-4 border-t border-ink/5">
            <Badge tone="stone" size="sm">
              + ~30 más en /mcp/v1/list_tools
            </Badge>
          </div>
        </Card>
      </Stagger>
    </Surface>
  );
}

function CopyableCode({ value, multiline }: { value: string; multiline?: boolean }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };
  return (
    <div className="relative group">
      <pre
        className={cn(
          "bg-canvas border border-ink/8 rounded-card px-4 py-3 text-xs text-ink overflow-x-auto",
          multiline ? "whitespace-pre" : "whitespace-pre-wrap break-all",
        )}
      >
        {value}
      </pre>
      <Button
        size="sm"
        variant="ghost"
        onClick={onCopy}
        leadingIcon={copied ? <Check size={12} /> : <Copy size={12} />}
        className="absolute top-2 right-2 bg-surface hover:bg-surface/80"
      >
        {copied ? "Copiado" : "Copiar"}
      </Button>
    </div>
  );
}
