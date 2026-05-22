/**
 * Keyboard shortcuts cheatsheet overlay.
 *
 * Opens with `?` (when not typing in a field). Lists every global shortcut
 * and the chord-style "G then X" navigation aliases. Mounted next to
 * CommandPalette so they don't fight for the Escape key.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Keyboard, X } from "lucide-react";
import { cn } from "@/ui";

interface ShortcutGroup {
  label: string;
  rows: { keys: string[]; description: string }[];
}

const GROUPS: ShortcutGroup[] = [
  {
    label: "Globales",
    rows: [
      { keys: ["⌘", "K"], description: "Abrir buscador / paleta de comandos" },
      { keys: ["?"], description: "Mostrar esta ayuda" },
      { keys: ["Esc"], description: "Cerrar diálogos y paneles" },
    ],
  },
  {
    label: "Navegación rápida",
    rows: [
      { keys: ["G", "C"], description: "Ir al chat" },
      { keys: ["G", "U"], description: "Ir al universo" },
      { keys: ["G", "J"], description: "Ir a ofertas" },
      { keys: ["G", "V"], description: "Generar CV" },
      { keys: ["G", "P"], description: "Preferencias de carrera" },
      { keys: ["G", "S"], description: "Ajustes" },
    ],
  },
  {
    label: "En la paleta",
    rows: [
      { keys: ["↑", "↓"], description: "Mover selección" },
      { keys: ["↵"], description: "Abrir / ejecutar" },
    ],
  },
  {
    label: "En el tour",
    rows: [
      { keys: ["→"], description: "Siguiente paso" },
      { keys: ["←"], description: "Anterior" },
      { keys: ["Esc"], description: "Saltar tour" },
    ],
  },
];

let externalOpen: (() => void) | null = null;
export function openShortcuts() {
  externalOpen?.();
}

const NAV_MAP: Record<string, string> = {
  c: "#/",
  u: "#/universe",
  j: "#/jobs",
  v: "#/cv/new",
  p: "#/preferences",
  s: "#/settings",
};

function isTypingTarget(el: EventTarget | null): boolean {
  const node = el as HTMLElement | null;
  if (!node) return false;
  const tag = node.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (node.isContentEditable) return true;
  return false;
}

export function ShortcutsOverlay() {
  const [open, setOpen] = useState(false);
  const [chord, setChord] = useState(false);

  useEffect(() => {
    externalOpen = () => setOpen(true);
    return () => {
      if (externalOpen) externalOpen = null;
    };
  }, []);

  // Chord-style "G then X" sequence for quick nav.
  useEffect(() => {
    if (!chord) return;
    const t = setTimeout(() => setChord(false), 1200);
    return () => clearTimeout(t);
  }, [chord]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const key = e.key.toLowerCase();
      if (key === "?" || (e.shiftKey && key === "/")) {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (e.key === "Escape" && open) {
        e.preventDefault();
        setOpen(false);
        return;
      }
      if (key === "g") {
        setChord(true);
        return;
      }
      if (chord && NAV_MAP[key]) {
        e.preventDefault();
        window.location.hash = NAV_MAP[key];
        setChord(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, chord]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="shortcuts"
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Atajos de teclado"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <motion.button
            type="button"
            aria-label="Cerrar"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-ink/35 backdrop-blur-sm cursor-default"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.div
            className="relative w-full max-w-xl rounded-card bg-canvas shadow-lift border border-ink/8 overflow-hidden"
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.97 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <header className="flex items-center justify-between px-5 py-4 border-b border-ink/5">
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-leaf-soft text-leaf-ink"
                >
                  <Keyboard size={14} />
                </span>
                <h2 className="text-heading-sm font-medium tracking-tight">
                  Atajos de teclado
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Cerrar"
                className="w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors"
              >
                <X size={14} />
              </button>
            </header>
            <div className="px-5 py-4 grid sm:grid-cols-2 gap-x-8 gap-y-5 max-h-[70vh] overflow-y-auto">
              {GROUPS.map((g) => (
                <section key={g.label}>
                  <h3 className="text-[11px] uppercase tracking-wider text-stone font-medium mb-2">
                    {g.label}
                  </h3>
                  <ul className="space-y-1.5">
                    {g.rows.map((row) => (
                      <li
                        key={row.description}
                        className="flex items-center justify-between gap-3 text-sm"
                      >
                        <span className="text-ink truncate">{row.description}</span>
                        <span className="flex items-center gap-1 shrink-0">
                          {row.keys.map((k, i) => (
                            <kbd
                              key={`${k}-${i}`}
                              className={cn(
                                "inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded-md bg-surface text-[10px] font-medium text-ink border border-ink/8",
                              )}
                            >
                              {k}
                            </kbd>
                          ))}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
            <footer className="px-5 py-3 bg-surface/40 border-t border-ink/5 text-[11px] text-stone">
              {chord ? (
                <span className="font-medium text-ink">
                  Esperando segunda tecla…
                </span>
              ) : (
                <>Pulsa <kbd className="bg-canvas px-1.5 py-0.5 rounded">?</kbd> en cualquier momento.</>
              )}
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
