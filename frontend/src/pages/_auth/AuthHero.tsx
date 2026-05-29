import { MessageSquare, Sparkles } from "lucide-react";
import { Reveal, Stagger, Badge } from "@/ui";

export interface AuthHeroProps {
  title: string;
  subtitle: string;
}

/**
 * Decorative split-screen hero for auth pages. Shows a mock chat
 * preview to communicate the chat-first nature of the product
 * before the user even logs in.
 */
export function AuthHero({ title, subtitle }: AuthHeroProps) {
  return (
    <div className="h-full flex flex-col justify-between p-10 lg:p-12 xl:p-16 gap-12 relative overflow-hidden">
      <div aria-hidden className="absolute -top-32 -right-32 w-[420px] h-[420px] rounded-full bg-sunbeam/35 blur-3xl" />
      <div aria-hidden className="absolute -bottom-40 -left-20 w-[380px] h-[380px] rounded-full bg-leaf/25 blur-3xl" />

      <div className="relative space-y-3">
        <Reveal>
          <span className="inline-flex items-center gap-2 text-ink font-medium">
            <span aria-hidden className="relative inline-block">
              <span className="inline-block w-8 h-8 rounded-full bg-leaf" />
              <span className="absolute inset-0.5 rounded-full bg-canvas grid place-items-center text-[13px] font-medium text-ink">
                u
              </span>
            </span>
            Universo Profesional
          </span>
        </Reveal>
      </div>

      <div className="relative space-y-6 max-w-md">
        <Reveal delay={0.08}>
          <h2 className="font-display text-[40px] xl:text-[52px] leading-[1.05] tracking-tight text-ink">
            {title}
          </h2>
        </Reveal>
        <Reveal delay={0.14}>
          <p className="text-body-lg text-stone">{subtitle}</p>
        </Reveal>

        <Stagger className="space-y-3 pt-4" delayStep={0.07} initialDelay={0.2}>
          <ChatBubble
            from="agent"
            icon={<Sparkles size={14} />}
            text="¿Cuál es el último proyecto que te ha hecho aprender algo?"
          />
          <ChatBubble from="user" text="Migré nuestro stack a Rust el último trimestre…" />
          <ChatBubble
            from="agent"
            icon={<MessageSquare size={14} />}
            text="Propongo añadirlo como experience. Confirma con un toque."
          />
        </Stagger>
      </div>

      <div className="relative flex flex-wrap gap-2">
        <Badge tone="sunbeam">CV generado en 8 segundos</Badge>
        <Badge tone="leaf" dot>
          Compatible con MCP
        </Badge>
      </div>
    </div>
  );
}

function ChatBubble({
  from,
  icon,
  text,
}: {
  from: "user" | "agent";
  icon?: React.ReactNode;
  text: string;
}) {
  if (from === "user") {
    return (
      <div className="ml-auto max-w-[85%] rounded-2xl bg-ink text-canvas px-4 py-2.5 text-sm shadow-soft">
        {text}
      </div>
    );
  }
  return (
    <div className="max-w-[90%] rounded-2xl bg-canvas px-4 py-2.5 text-sm shadow-soft flex items-start gap-2.5">
      {icon && (
        <span
          aria-hidden
          className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-leaf-soft text-leaf-ink shrink-0 mt-0.5"
        >
          {icon}
        </span>
      )}
      <span className="text-ink">{text}</span>
    </div>
  );
}
