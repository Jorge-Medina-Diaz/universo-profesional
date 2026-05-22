import { Sun, Moon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useTheme } from "@/shared/useTheme";
import { cn } from "@/ui";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Activar tema claro" : "Activar tema oscuro"}
      aria-pressed={isDark}
      className={cn(
        "relative inline-flex items-center justify-center w-9 h-9 rounded-full text-stone hover:text-ink hover:bg-surface transition-colors duration-180 ease-pirsch",
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          <motion.span
            key="moon"
            initial={{ opacity: 0, rotate: -90, scale: 0.6 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 90, scale: 0.6 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
            aria-hidden
          >
            <Moon size={16} />
          </motion.span>
        ) : (
          <motion.span
            key="sun"
            initial={{ opacity: 0, rotate: 90, scale: 0.6 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: -90, scale: 0.6 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
            aria-hidden
          >
            <Sun size={16} />
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}
