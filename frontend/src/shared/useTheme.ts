import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "cvs-saas-theme";

function readStoredTheme(): Theme | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

function resolveInitial(): Theme {
  // Light by default; respect an explicit stored choice. We intentionally do
  // NOT auto-follow prefers-color-scheme so the public landing opens light.
  const stored = readStoredTheme();
  if (stored) return stored;
  return "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function useTheme(): { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void } {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") return "light";
    const t = resolveInitial();
    applyTheme(t);
    return t;
  });

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return {
    theme,
    setTheme: setThemeState,
    toggle: () => setThemeState((t) => (t === "dark" ? "light" : "dark")),
  };
}
