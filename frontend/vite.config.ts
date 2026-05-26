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
          if (id.includes("/vaul/")) return "vaul";
          if (id.includes("lucide-react")) return "icons";
          if (id.includes("@fontsource/")) return "fonts";
          if (
            id.includes("/shiki/") ||
            id.includes("/mermaid/") ||
            id.includes("/highlight.js/") ||
            id.includes("/prismjs/")
          ) {
            return "syntax";
          }
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
