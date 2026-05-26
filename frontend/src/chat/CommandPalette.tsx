/**
 * Slash-command palette for the chat composer.
 *
 * Triggered when the user types `/` at the start of the input. Provides
 * contextual shortcuts that expand into full prompts or actions.
 */
import { useMemo, useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import { FileText, Target, Globe, Briefcase, ArrowUpRight } from "lucide-react";
import { cn } from "@/ui";

export interface SlashCommand {
  id: string;
  command: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  /** Full prompt to inject when selected. */
  prompt: string;
}

const COMMANDS: SlashCommand[] = [
  {
    id: "cv",
    command: "/cv",
    label: "Generar CV",
    description: "Crea un CV adaptado a una oferta o perfil",
    icon: <FileText size={14} strokeWidth={2} />,
    prompt: "Genera un CV profesional basado en mi perfil actual.",
  },
  {
    id: "goal",
    command: "/goal",
    label: "Añadir meta",
    description: "Define una nueva meta profesional",
    icon: <Target size={14} strokeWidth={2} />,
    prompt: "Quiero añadir una nueva meta profesional. Ayúdame a definirla.",
  },
  {
    id: "sync-github",
    command: "/sync github",
    label: "Sincronizar GitHub",
    description: "Importa repos y contribuciones",
    icon: <Globe size={14} strokeWidth={2} />,
    prompt: "Sincroniza mis datos de GitHub con mi perfil.",
  },
  {
    id: "job",
    command: "/job",
    label: "Ver jobs",
    description: "Lista tus oportunidades activas",
    icon: <Briefcase size={14} strokeWidth={2} />,
    prompt: "Muéstrame mis jobs activos y su estado actual.",
  },
];

export interface CommandPaletteHandle {
  open: () => void;
  close: () => void;
  isOpen: boolean;
  activeIndex: number;
  moveDown: () => void;
  moveUp: () => void;
  selectActive: () => void;
}

interface Props {
  query: string;
  onSelect: (cmd: SlashCommand) => void;
  onClose: () => void;
}

export const CommandPalette = forwardRef<CommandPaletteHandle, Props>(
  function CommandPalette({ query, onSelect, onClose }, ref) {
    const [activeIndex, setActiveIndex] = useState(0);
    const listRef = useRef<HTMLDivElement>(null);
    const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

    const filtered = useMemo(() => {
      const q = query.trim().toLowerCase();
      if (!q || q === "/") return COMMANDS;
      return COMMANDS.filter(
        (c) =>
          c.command.toLowerCase().includes(q) ||
          c.label.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q),
      );
    }, [query]);

    const isOpen = filtered.length > 0 && query.startsWith("/");

    useImperativeHandle(ref, () => ({
      open: () => {},
      close: onClose,
      isOpen,
      activeIndex,
      moveDown: () => setActiveIndex((i) => (i + 1) % filtered.length),
      moveUp: () => setActiveIndex((i) => (i - 1 + filtered.length) % filtered.length),
      selectActive: () => {
        const cmd = filtered[activeIndex];
        if (cmd) onSelect(cmd);
      },
    }));

    useEffect(() => {
      setActiveIndex(0);
    }, [query]);

    // Keyboard navigation is now handled by the parent Composer via
    // the imperative handle, avoiding a global window listener that
    // could steal focus from modals or other inputs.

    useEffect(() => {
      const el = itemRefs.current[activeIndex];
      if (el) el.scrollIntoView({ block: "nearest" });
    }, [activeIndex]);

    if (!isOpen) return null;

    return (
      <div
        ref={listRef}
        className="command-palette"
        role="listbox"
        aria-label="Comandos disponibles"
      >
        {filtered.map((cmd, i) => (
          <button
            key={cmd.id}
            ref={(el) => { itemRefs.current[i] = el; }}
            type="button"
            role="option"
            aria-selected={i === activeIndex}
            onClick={() => onSelect(cmd)}
            onMouseEnter={() => setActiveIndex(i)}
            className={cn("command-palette__item", i === activeIndex && "command-palette__item--active")}
          >
            <span className="command-palette__icon">{cmd.icon}</span>
            <span className="command-palette__text">
              <span className="command-palette__label">
                {cmd.label}
                <span className="command-palette__cmd">{cmd.command}</span>
              </span>
              <span className="command-palette__desc">{cmd.description}</span>
            </span>
            <ArrowUpRight size={12} className="command-palette__arrow" />
          </button>
        ))}
      </div>
    );
  },
);
