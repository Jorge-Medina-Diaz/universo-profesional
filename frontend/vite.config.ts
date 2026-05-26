import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": { target: "http://backend:8000", changeOrigin: true },
      "/auth": { target: "http://backend:8000", changeOrigin: true },
      "/mcp": { target: "http://backend:8000", changeOrigin: true },
      "/agui": { target: "http://backend:8000", changeOrigin: true },
      "/.well-known": { target: "http://backend:8000", changeOrigin: true },
    },
  },
  build: {
    // Heavy syntax-highlighter chunks (mermaid, shiki) live in their own
    // bundles below; raise the warning threshold accordingly.
    chunkSizeWarningLimit: 1000,
    // Do not modulepreload chunks that are only needed inside lazy-loaded
    // routes (copilotkit, syntax/GraphView, vaul). This saves ~6 MB of
    // eager download for anonymous users who only see the landing page.
    modulePreload: {
      resolveDependencies(_url, deps) {
        return deps.filter(
          (d) => !/copilotkit|syntax|GraphView|vaul/.test(d),
        );
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("@copilotkit/")) return "copilotkit";
          if (id.includes("/motion/") || id.includes("/framer-motion/")) {
            return "motion";
          }
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/scheduler/")
          ) {
            return "react";
          }
          if (id.includes("@tanstack/")) return "tanstack";
          if (id.includes("react-i18next") || id.includes("/i18next/")) {
            return "i18n";
          }
          // vaul is small (66 KB) and now lazy-loaded via WidgetsSheet.
          // Forcing it into its own chunk creates a false circular-dep
          // warning with the react chunk; let Rollup decide.
          if (id.includes("lucide-react")) return "icons";
          if (id.includes("@fontsource/")) return "fonts";
          // shiki / mermaid / highlight deps are pulled in exclusively by
          // CopilotKit. Forcing them into a separate "syntax" chunk creates a
          // circular dependency (syntax -> copilotkit -> syntax). Let Rollup keep
          // them inside the copilotkit lazy chunk instead.
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
  },
});
