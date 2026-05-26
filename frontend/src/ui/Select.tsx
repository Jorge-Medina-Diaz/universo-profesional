import { useState, useRef, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { useClickOutside } from "@/shared/useClickOutside";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { cn } from "./cn";

interface SelectOption {
  value: string;
  label: ReactNode;
}

export interface SelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

/**
 * Custom accessible select dropdown.
 */
export function Select({
  options,
  value,
  onChange,
  placeholder = "Seleccionar...",
  className,
  disabled,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);

  useClickOutside(ref, () => setOpen(false), open);
  useEscapeKey(() => setOpen(false), open);

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-input border border-hairline bg-canvas px-3 py-2 text-sm text-ink transition-colors hover:border-hairline-strong",
          disabled && "opacity-50 cursor-not-allowed",
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="truncate">{selected?.label ?? placeholder}</span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 text-stone transition-transform", open && "rotate-180")}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.14 }}
            role="listbox"
            className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-input border border-hairline bg-canvas shadow-float"
          >
            {options.map((option) => (
              <li
                key={option.value}
                role="option"
                aria-selected={option.value === value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "cursor-pointer px-3 py-2 text-sm transition-colors",
                  option.value === value
                    ? "bg-surface text-ink font-medium"
                    : "text-ink hover:bg-surface",
                )}
              >
                {option.label}
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
