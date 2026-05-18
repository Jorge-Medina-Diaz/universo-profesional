/**
 * Mobile bottom navigation. Active route highlighted via hash matching.
 */
import { useEffect, useState } from "react";

const ITEMS = [
  { href: "#/universe", icon: "🪐", label: "Universo" },
  { href: "#/connections", icon: "🔗", label: "Conexiones" },
  { href: "#/cv/new", icon: "📄", label: "CV" },
  { href: "#/settings", icon: "⚙️", label: "Ajustes" },
];

export function BottomNav() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return (
    <nav
      aria-label="Main navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-20 border-t border-gray-200 bg-white pb-[env(safe-area-inset-bottom)]"
    >
      <ul className="grid grid-cols-4">
        {ITEMS.map((it) => {
          const active = hash.startsWith(it.href);
          return (
            <li key={it.href}>
              <a
                href={it.href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center justify-center py-2 text-[11px] gap-0.5 h-14 ${
                  active ? "text-brand-700" : "text-gray-500 hover:text-gray-900"
                }`}
              >
                <span aria-hidden className="text-lg leading-none">{it.icon}</span>
                <span>{it.label}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
