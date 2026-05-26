import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import {
  MessageSquare,
  Sparkles,
  Plug,
  Settings,
  FileText,
  NotebookPen,
  Terminal,
  Search,
  CornerDownLeft,
  Wand2,
  Receipt,
  Activity as ActivityIcon,
  Heart,
  Briefcase,
  GraduationCap,
  Folder,
  Award,
  Languages,
  BookOpen,
  Trophy,
  StickyNote,
  ArrowLeftRight,
} from "lucide-react";
import { universe, type UniverseSearchHit } from "@/shared/api";
import { cn } from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

interface Command {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  shortcut?: string[];
  run: () => void;
}

const NAV_COMMANDS: Command[] = [
  {
    id: "chat",
    label: "Ir al chat",
    description: "Tu universo profesional en conversación",
    icon: <MessageSquare size={16} />,
    shortcut: ["G", "C"],
    run: () => (window.location.hash = "#/"),
  },
  {
    id: "universe",
    label: "Ver universo",
    description: "Educación, experiencia, proyectos, skills",
    icon: <Sparkles size={16} />,
    shortcut: ["G", "U"],
    run: () => (window.location.hash = "#/universe"),
  },
  {
    id: "connections",
    label: "Conexiones",
    description: "GitHub, LinkedIn, PDF",
    icon: <Plug size={16} />,
    run: () => (window.location.hash = "#/connections"),
  },
  {
    id: "cv",
    label: "Generar CV",
    description: "Adapta tu universo a una oferta",
    icon: <Wand2 size={16} />,
    shortcut: ["G", "V"],
    run: () => (window.location.hash = "#/cv/new"),
  },
  {
    id: "documents",
    label: "Documentos",
    description: "Histórico de CVs y cartas",
    icon: <FileText size={16} />,
    run: () => (window.location.hash = "#/documents"),
  },
  {
    id: "compare",
    label: "Comparar documentos",
    description: "A/B side-by-side",
    icon: <ArrowLeftRight size={16} />,
    run: () => (window.location.hash = "#/compare"),
  },
  {
    id: "notes",
    label: "Notas",
    description: "Capturas narrativas",
    icon: <NotebookPen size={16} />,
    run: () => (window.location.hash = "#/notes"),
  },
  {
    id: "mcp",
    label: "MCP",
    description: "Conecta Claude, Codex, Cursor",
    icon: <Terminal size={16} />,
    run: () => (window.location.hash = "#/mcp"),
  },
  {
    id: "activity",
    label: "Actividad",
    description: "Tu historia con el universo",
    icon: <ActivityIcon size={16} />,
    run: () => (window.location.hash = "#/activity"),
  },
  {
    id: "jobs",
    label: "Ofertas",
    description: "Pipeline kanban de tu búsqueda",
    icon: <Briefcase size={16} />,
    run: () => (window.location.hash = "#/jobs"),
  },
  {
    id: "preferences",
    label: "Preferencias de carrera",
    description: "Qué buscas, dónde, cuánto, cómo",
    icon: <Heart size={16} />,
    run: () => (window.location.hash = "#/preferences"),
  },
  {
    id: "billing",
    label: "Suscripción",
    description: "Plan, límites, upgrade",
    icon: <Receipt size={16} />,
    run: () => (window.location.hash = "#/billing"),
  },
  {
    id: "settings",
    label: "Ajustes",
    description: "Cuenta, RGPD, plan",
    icon: <Settings size={16} />,
    shortcut: ["G", "S"],
    run: () => (window.location.hash = "#/settings"),
  },
];

const HIT_META: Record<string, { label: string; Icon: typeof Briefcase; iconBg: string }> = {
  experience: { label: "Experiencia", Icon: Briefcase, iconBg: "bg-leaf-soft text-leaf-ink" },
  education: { label: "Educación", Icon: GraduationCap, iconBg: "bg-leaf-soft text-leaf-ink" },
  project: { label: "Proyecto", Icon: Folder, iconBg: "bg-sunbeam-soft text-sunbeam-ink" },
  skill: { label: "Skill", Icon: Sparkles, iconBg: "bg-sunbeam-soft text-sunbeam-ink" },
  certification: { label: "Certificación", Icon: Award, iconBg: "bg-leaf-soft text-leaf-ink" },
  course: { label: "Curso", Icon: BookOpen, iconBg: "bg-leaf-soft text-leaf-ink" },
  language: { label: "Idioma", Icon: Languages, iconBg: "bg-black/[0.04] text-stone" },
  achievement: { label: "Logro", Icon: Trophy, iconBg: "bg-sunbeam-soft text-sunbeam-ink" },
  note: { label: "Nota", Icon: StickyNote, iconBg: "bg-black/[0.04] text-stone" },
};

const FALLBACK_META = {
  label: "Universo",
  Icon: Sparkles,
  iconBg: "bg-black/[0.04] text-stone",
};

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="px-4 pt-3 pb-1.5 text-[10px] uppercase tracking-wider text-stone font-medium">
      {label}
    </div>
  );
}

let externalOpen: (() => void) | null = null;
export function openCommandPalette() {
  externalOpen?.();
}

/**
 * Cmd+K / Ctrl+K command palette. Provides quick nav across the whole app
 * regardless of the current page. Adds a sense of "everything is one toggle
 * away" — important for the chat-first product feel.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    externalOpen = () => setOpen(true);
    return () => {
      externalOpen = null;
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isCmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
      if (isCmdK) {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (e.key === "Escape" && open) {
        e.preventDefault();
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open]);

  const trimmed = query.trim();

  const filteredCommands = useMemo(() => {
    const q = trimmed.toLowerCase();
    if (!q) return NAV_COMMANDS;
    return NAV_COMMANDS.filter((c) => {
      const haystack = `${c.label} ${c.description ?? ""}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [trimmed]);

  // Universe search — only when the query is long enough and the palette is
  // open. Debounce by limiting to >=2 chars + react-query stale time.
  const searchEnabled = open && trimmed.length >= 2;
  const searchQuery = useQuery({
    queryKey: queryKeys.palette.search(trimmed),
    queryFn: () => universe.search(trimmed, 8),
    enabled: searchEnabled,
    staleTime: 30_000,
    retry: false,
  });

  const searchHits: UniverseSearchHit[] = searchEnabled ? (searchQuery.data ?? []) : [];
  const flatLength = filteredCommands.length + searchHits.length;

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const runCommand = (cmd: Command) => {
    cmd.run();
    setOpen(false);
  };

  const runHit = (hit: UniverseSearchHit) => {
    window.location.hash = `#/universe`;
    setOpen(false);
    // Persist a hint so UniversePage could scroll-to / highlight in a future iteration.
    try {
      sessionStorage.setItem(
        "cvs-saas-last-search-hit",
        JSON.stringify({ entity_type: hit.entity_type, entity_id: hit.entity_id }),
      );
    } catch {
      /* ignore */
    }
  };

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatLength - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex < filteredCommands.length) {
        const cmd = filteredCommands[activeIndex];
        if (cmd) runCommand(cmd);
      } else {
        const hit = searchHits[activeIndex - filteredCommands.length];
        if (hit) runHit(hit);
      }
    }
  };

  useEffect(() => {
    const node = listRef.current?.querySelector(`[data-index="${activeIndex}"]`);
    node?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="palette"
          role="dialog"
          aria-modal="true"
          aria-label="Comandos rápidos"
          className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <motion.button
            type="button"
            aria-label="Cerrar"
            className="absolute inset-0 bg-ink/30 backdrop-blur-sm cursor-default"
            onClick={() => setOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.div
            className="relative w-full max-w-xl rounded-card bg-canvas shadow-lift overflow-hidden"
            initial={{ opacity: 0, y: -10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <div className="flex items-center gap-3 px-4 border-b border-ink/8">
              <Search size={16} className="text-stone shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onInputKeyDown}
                placeholder="Salta a cualquier sitio…"
                className="flex-1 h-12 bg-transparent text-ink placeholder:text-stone outline-none text-sm"
                aria-controls="palette-list"
              />
              <kbd className="hidden sm:inline-flex items-center gap-1 text-[10px] text-stone bg-surface px-2 py-1 rounded-md font-medium">
                ESC
              </kbd>
            </div>
            <div
              id="palette-list"
              ref={listRef}
              role="listbox"
              className="max-h-[55vh] overflow-y-auto py-2"
            >
              {flatLength === 0 && !searchQuery.isFetching ? (
                <div className="px-4 py-8 text-center text-sm text-stone">
                  Sin resultados para "{query}"
                </div>
              ) : (
                <>
                  {filteredCommands.length > 0 && (
                    <>
                      <SectionHeader label="Navegación" />
                      {filteredCommands.map((cmd, i) => {
                        const idx = i;
                        const active = idx === activeIndex;
                        return (
                          <button
                            key={cmd.id}
                            type="button"
                            data-index={idx}
                            role="option"
                            aria-selected={active}
                            onClick={() => runCommand(cmd)}
                            onMouseEnter={() => setActiveIndex(idx)}
                            className={cn(
                              "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-180 ease-pirsch",
                              active ? "bg-surface" : "hover:bg-surface/60",
                            )}
                          >
                            <span
                              aria-hidden
                              className={cn(
                                "inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0 transition-colors",
                                active ? "bg-canvas text-ink" : "bg-surface text-stone",
                              )}
                            >
                              {cmd.icon}
                            </span>
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium text-ink truncate">
                                {cmd.label}
                              </div>
                              {cmd.description && (
                                <div className="text-xs text-stone truncate">
                                  {cmd.description}
                                </div>
                              )}
                            </div>
                            {active && (
                              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] text-stone">
                                <CornerDownLeft size={12} />
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </>
                  )}

                  {searchEnabled && (
                    <>
                      <SectionHeader
                        label={
                          searchQuery.isFetching
                            ? "Buscando en tu universo…"
                            : searchHits.length > 0
                              ? "En tu universo"
                              : "En tu universo · sin resultados"
                        }
                      />
                      {searchHits.map((hit, i) => {
                        const idx = filteredCommands.length + i;
                        const active = idx === activeIndex;
                        const meta = HIT_META[hit.entity_type] ?? FALLBACK_META;
                        const Icon = meta.Icon;
                        const label =
                          hit.preview ||
                          (hit.payload?.name as string | undefined) ||
                          (hit.payload?.title as string | undefined) ||
                          hit.entity_id.slice(0, 8);
                        return (
                          <button
                            key={`${hit.entity_type}-${hit.entity_id}`}
                            type="button"
                            data-index={idx}
                            role="option"
                            aria-selected={active}
                            onClick={() => runHit(hit)}
                            onMouseEnter={() => setActiveIndex(idx)}
                            className={cn(
                              "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-180 ease-pirsch",
                              active ? "bg-surface" : "hover:bg-surface/60",
                            )}
                          >
                            <span
                              aria-hidden
                              className={cn(
                                "inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0",
                                meta.iconBg,
                              )}
                            >
                              <Icon size={14} />
                            </span>
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium text-ink truncate">
                                {label}
                              </div>
                              <div className="text-xs text-stone truncate capitalize">
                                {meta.label} · {(hit.score * 100).toFixed(0)}% match
                              </div>
                            </div>
                            {active && (
                              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] text-stone">
                                <CornerDownLeft size={12} />
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </>
                  )}
                </>
              )}
            </div>
            <div className="flex items-center justify-between px-4 py-2 border-t border-ink/5 text-[11px] text-stone bg-surface/40">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1">
                  <kbd className="bg-canvas px-1.5 py-0.5 rounded">↑</kbd>
                  <kbd className="bg-canvas px-1.5 py-0.5 rounded">↓</kbd>
                  navegar
                </span>
                <span className="inline-flex items-center gap-1">
                  <kbd className="bg-canvas px-1.5 py-0.5 rounded">↵</kbd>
                  abrir
                </span>
              </div>
              <span className="hidden md:inline">
                {flatLength} {flatLength === 1 ? "resultado" : "resultados"}
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
