import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke test config for the Docker production stack.
 * Points at localhost:8080 (nginx frontend) instead of the Vite dev server.
 */
export default defineConfig({
  testDir: ".",
  fullyParallel: false,
  forbidOnly: false,
  retries: 1,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://localhost:8080",
    locale: "es-ES",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
