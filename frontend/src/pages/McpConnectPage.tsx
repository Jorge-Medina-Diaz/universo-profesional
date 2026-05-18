import { useTranslation } from "react-i18next";

export function McpConnectPage() {
  const { t } = useTranslation();
  const base = window.location.origin;
  const endpoint = `${base}/mcp`;

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{t("mcp.title")}</h1>
        <p className="text-gray-600">{t("mcp.intro")}</p>
      </header>

      <section className="card">
        <h2 className="font-semibold mb-2">{t("mcp.endpoint")}</h2>
        <code className="block bg-gray-50 p-2 rounded">{endpoint}</code>
        <p className="text-xs text-gray-500 mt-2">
          Auth: OAuth 2.1 + PKCE + DCR. Metadatos en{" "}
          <a className="underline" href="/.well-known/oauth-authorization-server" target="_blank" rel="noreferrer">/.well-known/oauth-authorization-server</a>.
        </p>
      </section>

      <section className="space-y-3">
        <ClientCard
          name="Claude Code / Claude Desktop"
          command={`claude mcp add --transport http cvs-saas ${endpoint}`}
          notes="Se abrirá el navegador para completar el flujo OAuth."
        />
        <ClientCard
          name="Codex (OpenAI)"
          command={`codex mcp add cvs-saas ${endpoint}`}
        />
        <ClientCard
          name="Cursor"
          command={`# .cursor/mcp.json
{
  "mcpServers": {
    "cvs-saas": { "url": "${endpoint}" }
  }
}`}
        />
        <ClientCard
          name="Windsurf / Zed"
          command={`Endpoint: ${endpoint}\nTransport: streamable-http\nAuth: oauth2.1 (DCR)`}
        />
      </section>

      <section className="card">
        <h2 className="font-semibold mb-2">Herramientas disponibles</h2>
        <ul className="list-disc list-inside text-sm space-y-1">
          <li><strong>get_profile</strong> — Lee tu universo profesional</li>
          <li><strong>get_universe_summary</strong> — Resumen compacto</li>
          <li><strong>add_education</strong>, <strong>update_education</strong></li>
          <li><strong>add_experience</strong>, <strong>add_skill</strong></li>
          <li><strong>match_job_to_profile</strong> — Score JD ↔ universo</li>
          <li><strong>generate_cv</strong> — CV adaptado en PDF/DOCX/JSON</li>
        </ul>
      </section>
    </div>
  );
}

function ClientCard({ name, command, notes }: { name: string; command: string; notes?: string }) {
  return (
    <div className="card">
      <h3 className="font-semibold mb-2">{name}</h3>
      <pre className="bg-gray-50 p-2 rounded text-xs whitespace-pre-wrap">{command}</pre>
      {notes && <p className="text-xs text-gray-500 mt-2">{notes}</p>}
    </div>
  );
}
