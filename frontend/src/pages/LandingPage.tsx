import { Sparkles, MessageSquare, Plug } from "lucide-react";
import { Button, Card, Surface, Reveal, Stagger, Badge } from "@/ui";
import { CursorGlow } from "@/widgets/CursorGlow";

export function LandingPage() {
  return (
    <div className="bg-canvas relative overflow-hidden">
      <CursorGlow />
      <Surface width="lg" spacing="lg" className="text-center items-center pt-12 md:pt-24">
        <Reveal>
          <Badge tone="leaf" dot>
            Nuevo · Universo profesional conversacional
          </Badge>
        </Reveal>
        <Reveal delay={0.06}>
          <h1 className="font-display text-display-lg text-ink max-w-3xl">
            Sustituye el CV en Word por un{" "}
            <span className="bg-sunbeam text-ink px-3 rounded-[14px] inline-block leading-[1.05]">
              universo vivo
            </span>
          </h1>
        </Reveal>
        <Reveal delay={0.12}>
          <p className="text-body-lg text-stone max-w-xl">
            Habla con tu agente, importa LinkedIn, GitHub y tus PDFs, y genera CVs
            adaptados a cada oferta en segundos. Compatible con Claude, Codex y
            Cursor mediante MCP.
          </p>
        </Reveal>
        <Reveal delay={0.18}>
          <div className="flex flex-wrap gap-3 justify-center pt-2">
            <Button size="lg" onClick={() => (window.location.hash = "#/register")}>
              Empezar gratis
            </Button>
            <Button size="lg" variant="outline" onClick={() => (window.location.hash = "#/login")}>
              Ya tengo cuenta
            </Button>
          </div>
        </Reveal>
      </Surface>

      <Surface width="xl" spacing="md">
        <Stagger className="grid md:grid-cols-3 gap-4 md:gap-6" delayStep={0.06}>
          <Feature
            icon={<MessageSquare size={20} />}
            tone="leaf"
            title="Conversación primero"
            body="Cuéntale tu trayectoria al agente. Cada propuesta la confirmas tú con un toque."
          />
          <Feature
            icon={<Sparkles size={20} />}
            tone="sunbeam"
            title="Universo persistente"
            body="Un grafo vivo de tu carrera, no un documento estático. Crece contigo."
          />
          <Feature
            icon={<Plug size={20} />}
            tone="stone"
            title="MCP nativo"
            body="Conecta Claude Code, Codex y Cursor a tu universo con un solo clic."
          />
        </Stagger>
      </Surface>
    </div>
  );
}

function Feature({
  icon,
  tone,
  title,
  body,
}: {
  icon: React.ReactNode;
  tone: "leaf" | "sunbeam" | "stone";
  title: string;
  body: string;
}) {
  const ringClass =
    tone === "leaf"
      ? "bg-leaf-soft text-leaf-ink"
      : tone === "sunbeam"
        ? "bg-sunbeam-soft text-sunbeam-ink"
        : "bg-black/5 text-ink";
  return (
    <Card padding="lg" className="flex flex-col gap-4">
      <span
        aria-hidden
        className={`inline-flex items-center justify-center w-11 h-11 rounded-full ${ringClass}`}
      >
        {icon}
      </span>
      <div className="space-y-1">
        <h3 className="text-heading-sm font-medium tracking-tight">{title}</h3>
        <p className="text-stone leading-relaxed">{body}</p>
      </div>
    </Card>
  );
}
