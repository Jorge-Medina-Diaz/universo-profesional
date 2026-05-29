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
        "surface-base": "var(--surface-base)",
        "surface-raised": "var(--surface-raised)",
        field: "var(--surface-field)",
        hairline: "var(--hairline)",
        sunbeam: {
          DEFAULT: "var(--color-sunbeam-yellow)",
          soft: "var(--color-sunbeam-soft)",
          ink: "var(--color-sunbeam-ink)",
          hover: "var(--color-sunbeam-hover)",
        },
        leaf: {
          DEFAULT: "var(--color-leafy-green)",
          soft: "var(--color-leaf-soft)",
          ink: "var(--color-leaf-ink)",
          hover: "var(--color-leaf-hover)",
        },
        nova: {
          DEFAULT: "var(--color-nova)",
          soft: "var(--color-nova-soft)",
          ink: "var(--color-nova-ink)",
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
        display: [
          "Fraunces Variable",
          "Fraunces",
          "Georgia",
          "Times New Roman",
          "serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        eyebrow: ["11px", { lineHeight: "1", letterSpacing: "0.18em" }],
        body: ["16px", { lineHeight: "1.5", letterSpacing: "-0.016em" }],
        "body-lg": ["18px", { lineHeight: "1.55", letterSpacing: "-0.016em" }],
        subheading: ["20px", { lineHeight: "1.3", letterSpacing: "-0.016em" }],
        "heading-sm": ["24px", { lineHeight: "1.2", letterSpacing: "-0.018em" }],
        heading: ["28px", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        "heading-lg": ["36px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        display: ["clamp(40px, 6vw, 68px)", { lineHeight: "1.04", letterSpacing: "-0.022em" }],
        "display-lg": ["clamp(56px, 9vw, 116px)", { lineHeight: "0.98", letterSpacing: "-0.028em" }],
      },
      letterSpacing: {
        eyebrow: "0.18em",
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
        // Floating composer / overlay — deeper, for elements over the constellation.
        float: "0 4px 12px -2px rgba(0,0,0,0.08), 0 24px 60px -24px rgba(0,0,0,0.22)",
        "glow-leaf": "var(--glow-leaf)",
        "glow-sunbeam": "var(--glow-sunbeam)",
        "glow-nova": "var(--glow-nova)",
      },
      transitionTimingFunction: {
        pirsch: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
      transitionDuration: {
        180: "180ms",
        280: "280ms",
        420: "420ms",
      },
      animation: {
        marquee: "marquee 35s linear infinite",
        "gradient-shift": "gradient-shift 8s ease infinite",
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-33.333%)" },
        },
        "gradient-shift": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
