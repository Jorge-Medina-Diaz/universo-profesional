import { MessageSquare, Sparkles, Plug, Settings } from "lucide-react";
import { useHashRoute } from "@/shared/useHashRoute";
import { cn } from "@/ui/cn";

interface Tab {
  href: string;
  label: string;
  Icon: typeof MessageSquare;
  matches: (path: string) => boolean;
}

const TABS: Tab[] = [
  { href: "#/", label: "Chat", Icon: MessageSquare, matches: (p) => p === "/" || p.startsWith("/onboarding") },
  {
    href: "#/universe",
    label: "Universo",
    Icon: Sparkles,
    matches: (p) =>
      p.startsWith("/universe") || p.startsWith("/notes") || p.startsWith("/cv") || p.startsWith("/preferences"),
  },
  {
    href: "#/connections",
    label: "Conectar",
    Icon: Plug,
    matches: (p) =>
      p.startsWith("/connections") || p.startsWith("/documents") || p.startsWith("/mcp") || p.startsWith("/compare"),
  },
  {
    href: "#/settings",
    label: "Ajustes",
    Icon: Settings,
    matches: (p) => p.startsWith("/settings") || p.startsWith("/billing") || p.startsWith("/activity"),
  },
];

function haptic() {
  try {
    if (navigator.vibrate) navigator.vibrate(10);
  } catch {
    /* ignore */
  }
}

export function BottomNav() {
  const path = useHashRoute();
  return (
    <nav
      aria-label="Navegación principal"
      className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-canvas/95 backdrop-blur-md border-t border-ink/8 safe-bottom"
    >
      <ul className="grid grid-cols-4 px-2 py-1.5">
        {TABS.map(({ href, label, Icon, matches }) => {
          const active = matches(path);
          return (
            <li key={href}>
              <a
                href={href}
                onClick={() => haptic()}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 py-2 rounded-btn transition-colors duration-180 ease-pirsch select-none",
                  active ? "text-ink" : "text-stone hover:text-ink hover:bg-black/[0.03]",
                )}
              >
                <Icon
                  size={20}
                  strokeWidth={active ? 2.25 : 1.75}
                  aria-hidden
                  className={cn(active && "text-ink")}
                />
                <span className="text-[11px] font-medium leading-none">{label}</span>
                {active && (
                  <span
                    aria-hidden
                    className="absolute -bottom-1 h-1 w-1 rounded-full bg-leaf"
                  />
                )}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
