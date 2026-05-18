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
      "/.well-known": { target: "http://backend:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
