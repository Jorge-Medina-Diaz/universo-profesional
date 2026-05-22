import type { Config } from "tailwindcss";

/**
 * Design tokens are declared as CSS custom properties in src/styles/index.css.
 * This config maps semantic Tailwind utilities to those vars so the whole
 * theme is controlled from a single place (the :root block).
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic tokens — preferred for new code.
        ink: "var(--color-midnight-ink)",
        stone: "var(--color-muted-stone)",
        canvas: "var(--surface-canvas)",
        surface: "var(--surface-card-surface)",
        sunbeam: {
          DEFAULT: "var(--color-sunbeam-yellow)",
          soft: "var(--color-sunbeam-soft)",
          ink: "var(--color-sunbeam-ink)",
        },
        leaf: {
          DEFAULT: "var(--color-leafy-green)",
          soft: "var(--color-leaf-soft)",
          ink: "var(--color-leaf-ink)",
        },
        // Legacy `brand` alias — kept so existing `bg-brand-600`, `border-brand-200`
        // etc. compile during the rolling migration. All map to the new palette.
        brand: {
          50: "var(--color-leaf-soft)",
          100: "var(--color-leaf-soft)",
          200: "var(--color-leaf-soft)",
          500: "var(--color-leafy-green)",
          600: "var(--color-leafy-green)",
          700: "var(--color-leaf-ink)",
          800: "var(--color-midnight-ink)",
          900: "var(--color-midnight-ink)",
        },
      },
      fontFamily: {
        sans: [
          "DM Sans",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: ["DM Sans", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        body: ["16px", { lineHeight: "1.5", letterSpacing: "-0.016em" }],
        "body-lg": ["18px", { lineHeight: "1.5", letterSpacing: "-0.016em" }],
        subheading: ["20px", { lineHeight: "1.25", letterSpacing: "-0.016em" }],
        "heading-sm": ["24px", { lineHeight: "1.25", letterSpacing: "-0.016em" }],
        heading: ["28px", { lineHeight: "1.25", letterSpacing: "-0.016em" }],
        display: ["64px", { lineHeight: "1.05", letterSpacing: "-0.022em" }],
      },
      borderRadius: {
        input: "6px",
        btn: "12px",
        card: "24px",
        tag: "24px",
      },
      boxShadow: {
        // Soft Pirsch-style elevation — no harsh shadows, just a hint of depth.
        soft: "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px -12px rgba(0,0,0,0.08)",
        lift: "0 2px 4px rgba(0,0,0,0.04), 0 16px 40px -20px rgba(0,0,0,0.12)",
      },
      transitionTimingFunction: {
        pirsch: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
      transitionDuration: {
        180: "180ms",
        280: "280ms",
        420: "420ms",
      },
    },
  },
  plugins: [],
};

export default config;
