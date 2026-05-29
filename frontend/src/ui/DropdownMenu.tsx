import { useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useClickOutside } from "@/shared/useClickOutside";
import { useEscapeKey } from "@/shared/useEscapeKey";
import { cn } from "./cn";

export interface DropdownMenuProps {
  trigger: ReactNode;
  children: ReactNode;
  className?: string;
  align?: "start" | "end";
}

export interface DropdownMenuItemProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  destructive?: boolean;
  icon?: ReactNode;
  className?: string;
}

export function DropdownMenu({
  trigger,
  children,
  className,
  align = "start",
}: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false), open);
  useEscapeKey(() => setOpen(false), open);

  return (
    <div ref={ref} className="relative inline-block">
      <div
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(!open);
          }
        }}
        role="button"
        tabIndex={0}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {trigger}
      </div>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="menu"
            className={cn(
              "absolute z-40 min-w-[12rem] rounded-xl bg-canvas shadow-lg border border-ink/10 p-1",
              align === "start" ? "left-0" : "right-0",
              "top-full mt-2",
              className,
            )}
            initial={{ opacity: 0, scale: 0.96, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -4 }}
            transition={{ type: "spring", damping: 25, stiffness: 320 }}
          >
            {children}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

export function DropdownMenuItem({
  children,
  onClick,
  disabled,
  destructive,
  icon,
  className,
}: DropdownMenuItemProps) {
  return (
    <li role="menuitem">
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors",
          "hover:bg-black/5 focus-visible:outline-none focus-visible:bg-black/5",
          destructive && "text-red-600 hover:bg-red-50",
          disabled && "opacity-40 cursor-not-allowed",
          className,
        )}
      >
        {icon && <span className="inline-flex shrink-0">{icon}</span>}
        <span className="truncate">{children}</span>
      </button>
    </li>
  );
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return <li className={cn("my-1 h-px bg-ink/10", className)} role="separator" />;
}
